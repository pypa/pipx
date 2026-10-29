from __future__ import annotations

__lazy_modules__ = [
    "pipx",
    "pipx.backends.uv",
    "pipx.redact",
    "pipx.subprocess_runner",
    "pipx.util",
    "pipx.wrap",
    "shutil",
]

import logging
import os
from shutil import which
from typing import TYPE_CHECKING, Final, NoReturn

from pipx import paths
from pipx.backends.uv import PIP_TO_UV_INDEX_FLAGS, UvBackend, resolve_uv_binary
from pipx.emojis import HAZARD
from pipx.redact import redact_url_credentials
from pipx.subprocess_runner import exec_app
from pipx.util import PipxError
from pipx.wrap import pipx_wrap

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from pipx.options import RunOptions

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

_UV_FORMAT_CONTROL_FLAG_MAP: Final[dict[str, tuple[str, str]]] = {
    "--no-binary": ("--no-binary", "--no-binary-package"),
    "--only-binary": ("--no-build", "--no-build-package"),
}


def run_via_uv_tool_run(app: str, package_or_url: str, options: RunOptions) -> NoReturn:
    _reject_venv_args(options.venv_args)
    if not options.no_path_check and (existing_app_path := which(app)):
        _LOGGER.warning(
            pipx_wrap(
                f"""
                {HAZARD}  {app} is already on your PATH and installed at
                {existing_app_path}. Downloading and running anyway.
                """,
                subsequent_indent=" " * 4,
            )
        )

    cmd: list[str] = [str(resolve_uv_binary()), "tool", "run"]
    if package_or_url and package_or_url != app:
        cmd += ["--from", package_or_url]
    if options.python:
        cmd += ["--python", options.python]
    for dependency in options.dependencies:
        cmd += ["--with", dependency]
    if not options.use_cache:
        cmd.append("--no-cache")
    if options.refresh:
        cmd.append("--refresh")
    if options.verbose:
        cmd.append("--verbose")
    cmd += translate_pip_args_for_uv(options.pip_args)
    cmd += UvBackend.cooldown_args(options.cooldown.days)
    # without the separator uv reads an app name that starts with a dash as one of its own options
    cmd += ["--", app, *options.app_args]
    exec_app(cmd)


def _reject_venv_args(venv_args: list[str]) -> None:
    # uv creates the venv, so accepting these options would ignore the requested behavior
    if venv_args:
        msg = (
            f"{' '.join(map(redact_url_credentials, venv_args))} is not supported by `pipx run` under the uv backend.\n"
            "Use `pipx run --backend pip` if you need it, or drop it."
        )
        raise PipxError(msg)


def translate_pip_args_for_uv(pip_args: list[str]) -> list[str]:
    translated_bool_flags: Final[dict[str, str]] = {
        "--pre": "--prerelease=allow",
        "--no-cache-dir": "--no-cache",
        "--upgrade": "--upgrade",
        "-U": "--upgrade",
    }
    value_flags: Final[dict[str, str]] = {
        "--extra-index-url": "--extra-index-url",
        "--find-links": "--find-links",
        "-f": "-f",
        "--trusted-host": "--allow-insecure-host",
    }
    translated: Final[list[str]] = []
    iterator: Final[Iterator[str]] = iter(pip_args)
    for arg in iterator:
        if arg in {"-q", "-qq", "--quiet"}:
            continue
        if arg in {"--editable", "-e"}:
            msg = (
                "`--editable` is not supported by `pipx run --backend uv`.\n"
                "Use `pipx run --backend pip` for editable installs."
            )
            raise PipxError(msg)
        if (translated_bool := translated_bool_flags.get(arg)) is not None:
            translated.append(translated_bool)
            continue
        flag, separator, attached_value = arg.partition("=")
        if flag in _UV_FORMAT_CONTROL_FLAG_MAP:
            translated.extend(
                _translate_format_control(flag, attached_value if separator else _next_pip_arg(flag, iterator))
            )
            continue
        if (translated_flag := PIP_TO_UV_INDEX_FLAGS.get(flag) or value_flags.get(flag)) is not None:
            if separator:
                translated.append(f"{translated_flag}={attached_value}")
            else:
                translated.extend([translated_flag, _next_pip_arg(flag, iterator)])
            continue
        msg = (
            f"--pip-args contains {redact_url_credentials(arg)!r}, which has no `uv tool run` equivalent.\n"
            "Use `--backend pip` if you need pip-only flags."
        )
        raise PipxError(msg)
    return translated


def _translate_format_control(flag: str, value: str) -> list[str]:
    all_flag, package_flag = _UV_FORMAT_CONTROL_FLAG_MAP[flag]
    if value == ":all:":
        return [all_flag]
    if value == ":none:":
        return []
    if not all(packages := value.split(",")):
        msg = f"Invalid value for {flag!r} in --pip-args: {value!r}."
        raise PipxError(msg)
    return [item for package in packages for item in (package_flag, package)]


def _next_pip_arg(flag: str, iterator: Iterator[str]) -> str:
    try:
        return next(iterator)
    except StopIteration as exc:
        msg = f"Missing value for {flag!r} in --pip-args."
        raise PipxError(msg) from exc


def run_script_via_uv_run(script_path: Path, venv_dir: Path, options: RunOptions) -> NoReturn:
    _reject_venv_args(options.venv_args)
    # uv searches for project config from --project, or else from the script's directory, which another account may own
    cmd: list[str] = [str(resolve_uv_binary()), "run", "--active", "--script", "--project", str(paths.CTX.home)]
    if options.python:
        cmd += ["--python", options.python]
    if not options.use_cache:
        cmd.append("--no-cache")
    if options.refresh:
        cmd.append("--refresh")
    if options.verbose:
        cmd.append("--verbose")
    for dependency in options.dependencies:
        cmd += ["--with", dependency]
    cmd += translate_pip_args_for_uv(options.pip_args)
    cmd += UvBackend.cooldown_args(options.cooldown.days)
    cmd += [str(script_path), *options.app_args]
    exec_app(cmd, env={**os.environ, "VIRTUAL_ENV": str(venv_dir)})


__all__ = [
    "run_script_via_uv_run",
    "run_via_uv_tool_run",
    "translate_pip_args_for_uv",
]
