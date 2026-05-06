"""``pipx run`` delegation under the uv backend, kept out of ``run.py`` so the
flag-translation surface doesn't bury the pip flow."""

from __future__ import annotations

import logging
from shutil import which
from typing import TYPE_CHECKING, Final, NoReturn

from pipx.backends.uv import resolve_uv_binary
from pipx.emojis import hazard
from pipx.util import PipxError, exec_app, pipx_wrap

if TYPE_CHECKING:
    from pathlib import Path

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Pip flags translatable to ``uv tool run`` / ``uv run``; anything else errors.
_UV_TRANSLATABLE_VALUE_FLAGS: Final[frozenset[str]] = frozenset(
    {"--index-url", "-i", "--extra-index-url", "--find-links", "-f", "--no-binary", "--only-binary", "--trusted-host"}
)
_UV_TRANSLATABLE_BOOL_FLAGS: Final[dict[str, str]] = {
    "--pre": "--prerelease=allow",
    "--no-deps": "--no-deps",
    "--no-cache-dir": "--no-cache",
    "--upgrade": "--upgrade",
    "-U": "--upgrade",
}


def _reject_venv_args(venv_args: list[str]) -> None:
    # uv builds its own venv internally; silently dropping ``--venv-args``
    # (e.g. ``--system-site-packages``) would diverge from the pip path.
    if venv_args:
        raise PipxError(
            f"--venv-args ({' '.join(venv_args)}) is not supported by `pipx run --backend uv`.\n"
            "Use `pipx run --backend pip` if those flags are required, or drop them."
        )


def run_via_uv_tool_run(
    *,
    app: str,
    package_or_url: str,
    dependencies: list[str],
    app_args: list[str],
    python: str,
    pip_args: list[str],
    venv_args: list[str],
    use_cache: bool,
    verbose: bool,
) -> NoReturn:
    _reject_venv_args(venv_args)
    if existing_app_path := which(app):
        _LOGGER.warning(
            pipx_wrap(
                f"""
                {hazard}  {app} is already on your PATH and installed at
                {existing_app_path}. Downloading and running anyway.
                """,
                subsequent_indent=" " * 4,
            )
        )

    cmd: list[str] = [str(resolve_uv_binary()), "tool", "run"]
    if package_or_url and package_or_url != app:
        cmd += ["--from", package_or_url]
    if python:
        cmd += ["--python", python]
    for dependency in dependencies:
        cmd += ["--with", dependency]
    if not use_cache:
        cmd.append("--no-cache")
    if verbose:
        cmd.append("--verbose")
    cmd += translate_pip_args_for_uv(pip_args)
    cmd.append(app)
    cmd += app_args
    exec_app(cmd)


def run_script_via_uv_run(
    *,
    script_path: Path,
    app_args: list[str],
    python: str,
    pip_args: list[str],
    venv_args: list[str],
    use_cache: bool,
    verbose: bool,
    dependencies: list[str] | None = None,
) -> NoReturn:
    _reject_venv_args(venv_args)
    cmd: list[str] = [str(resolve_uv_binary()), "run", "--script"]
    if python:
        cmd += ["--python", python]
    if not use_cache:
        cmd.append("--no-cache")
    if verbose:
        cmd.append("--verbose")
    for dependency in dependencies or []:
        cmd += ["--with", dependency]
    cmd += translate_pip_args_for_uv(pip_args)
    cmd += [str(script_path), *app_args]
    exec_app(cmd)


def translate_pip_args_for_uv(pip_args: list[str]) -> list[str]:
    """Translate ``pip_args`` for ``uv tool run`` / ``uv run --script``.

    Strict on this boundary because ``uv tool run`` exposes a smaller flag
    surface than ``uv pip install``; the install path stays permissive (it
    forwards everything to uv) since over-rejecting valid uv pip flags would
    be more painful than the asymmetry.
    """
    translated: list[str] = []
    iterator = iter(pip_args)
    for arg in iterator:
        if arg in ("-q", "-qq", "--quiet"):
            continue
        if arg in ("--editable", "-e"):
            raise PipxError(
                "`--editable` is not supported by `pipx run --backend uv`.\n"
                "Use `pipx run --backend pip` for editable installs."
            )
        if (translated_bool := _UV_TRANSLATABLE_BOOL_FLAGS.get(arg)) is not None:
            translated.append(translated_bool)
            continue
        if arg in _UV_TRANSLATABLE_VALUE_FLAGS:
            try:
                value = next(iterator)
            except StopIteration as exc:
                raise PipxError(f"Missing value for {arg!r} in --pip-args.") from exc
            translated.extend([arg, value])
            continue
        # Bool flags must not accept ``=value`` (caught ``--pre=foo`` slipping through).
        if "=" in arg and arg.split("=", 1)[0] in _UV_TRANSLATABLE_VALUE_FLAGS:
            translated.append(arg)
            continue
        raise PipxError(
            f"--pip-args contains {arg!r}, which has no `uv tool run` equivalent.\n"
            "Use `--backend pip` if you need pip-only flags."
        )
    return translated


__all__ = [
    "run_script_via_uv_run",
    "run_via_uv_tool_run",
    "translate_pip_args_for_uv",
]
