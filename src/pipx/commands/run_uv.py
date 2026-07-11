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
    from collections.abc import Iterator
    from pathlib import Path

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

_UV_VALUE_FLAG_MAP: Final[dict[str, str]] = {
    "--index-url": "--index-url",
    "-i": "-i",
    "--extra-index-url": "--extra-index-url",
    "--find-links": "--find-links",
    "-f": "-f",
    "--trusted-host": "--allow-insecure-host",
}
_UV_FORMAT_CONTROL_FLAG_MAP: Final[dict[str, tuple[str, str]]] = {
    "--no-binary": ("--no-binary", "--no-binary-package"),
    "--only-binary": ("--no-build", "--no-build-package"),
}
_UV_TRANSLATABLE_BOOL_FLAGS: Final[dict[str, str]] = {
    "--pre": "--prerelease=allow",
    "--no-cache-dir": "--no-cache",
    "--upgrade": "--upgrade",
    "-U": "--upgrade",
}


def _next_pip_arg(flag: str, iterator: Iterator[str]) -> str:
    try:
        return next(iterator)
    except StopIteration as exc:
        raise PipxError(f"Missing value for {flag!r} in --pip-args.") from exc


def _translate_format_control(flag: str, value: str) -> list[str]:
    all_flag, package_flag = _UV_FORMAT_CONTROL_FLAG_MAP[flag]
    if value == ":all:":
        return [all_flag]
    if value == ":none:":
        return []
    if not all(packages := value.split(",")):
        raise PipxError(f"Invalid value for {flag!r} in --pip-args: {value!r}.")
    return [item for package in packages for item in (package_flag, package)]


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
    no_path_check: bool = False,
) -> NoReturn:
    _reject_venv_args(venv_args)
    if not no_path_check and (existing_app_path := which(app)):
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
        flag, separator, attached_value = arg.partition("=")
        if flag in _UV_FORMAT_CONTROL_FLAG_MAP:
            translated.extend(
                _translate_format_control(flag, attached_value if separator else _next_pip_arg(flag, iterator))
            )
            continue
        if (translated_flag := _UV_VALUE_FLAG_MAP.get(flag)) is not None:
            if separator:
                translated.append(f"{translated_flag}={attached_value}")
            else:
                translated.extend([translated_flag, _next_pip_arg(flag, iterator)])
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
