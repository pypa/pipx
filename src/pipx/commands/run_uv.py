from __future__ import annotations

from pipx.emojis import HAZARD

__lazy_modules__ = [
    "packaging.utils",
    "pipx.backends.uv",
    "pipx.paths",
    "pipx.redact",
    "pipx.subprocess_runner",
    "pipx.util",
    "pipx.wrap",
    "shutil",
]

import logging
import os
from shutil import which
from types import MappingProxyType
from typing import TYPE_CHECKING, Final, NoReturn

from packaging.utils import canonicalize_name

from pipx.backends.uv import PIP_TO_UV_INDEX_FLAGS, UvBackend, resolve_uv_binary
from pipx.paths import CTX
from pipx.redact import redact_url_credentials
from pipx.subprocess_runner import exec_app
from pipx.util import PipxError
from pipx.wrap import pipx_wrap

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from pipx.options import RunOptions

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

_UV_FORMAT_CONTROL_FLAG_MAP: Final[MappingProxyType[str, tuple[str, str]]] = MappingProxyType({
    "--no-binary": ("--no-binary", "--no-binary-package"),
    "--only-binary": ("--no-build", "--no-build-package"),
})


_UV_BOOL_FLAG_MAP: Final[MappingProxyType[str, str]] = MappingProxyType({
    "--pre": "--prerelease=allow",
    "--no-cache-dir": "--no-cache",
    "--upgrade": "--upgrade",
    "-U": "--upgrade",
})
_UV_VALUE_FLAG_MAP: Final[MappingProxyType[str, str]] = MappingProxyType({
    "--extra-index-url": "--extra-index-url",
    "--find-links": "--find-links",
    "-f": "-f",
    "--trusted-host": "--allow-insecure-host",
})


def run_via_uv_tool_run(app: str, package_or_url: str, options: RunOptions) -> NoReturn:
    """Run an app through ``uv tool run``, replacing the current process.

    :param app: the app name.
    :param package_or_url: the package spec or URL to install.
    :param options: the options of the run.
    :raises PipxError: when venv arguments are given, which ``uv tool run`` cannot take.
    """
    _reject_venv_args(options.venv_args)
    if not options.lookup.no_path_check and (existing_app_path := which(app)):
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
    if options.interpreter.python:
        cmd += ["--python", options.interpreter.python]
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
    """Translate pip install arguments into their uv equivalents.

    :param pip_args: the pip arguments to translate.
    :returns: the uv arguments.
    :raises PipxError: when an argument has no uv equivalent, such as ``--editable``.
    """
    format_control: Final[dict[str, set[str]]] = {flag: set() for flag in _UV_FORMAT_CONTROL_FLAG_MAP}
    translated: Final[list[str]] = []
    iterator: Final[Iterator[str]] = iter(pip_args)
    for arg in iterator:
        _translate_one_pip_arg(arg, iterator, translated, format_control)
    for flag, packages in format_control.items():
        all_flag, package_flag = _UV_FORMAT_CONTROL_FLAG_MAP[flag]
        if ":all:" in packages:
            translated.append(all_flag)
        else:
            for package in sorted(packages):
                translated.extend((package_flag, package))
    return translated


def _translate_one_pip_arg(
    arg: str,
    iterator: Iterator[str],
    translated: list[str],
    format_control: dict[str, set[str]],
) -> None:
    if arg in {"-q", "-qq", "--quiet"}:
        return
    if arg in {"--editable", "-e"}:
        msg = (
            "`--editable` is not supported by `pipx run --backend uv`.\n"
            "Use `pipx run --backend pip` for editable installs."
        )
        raise PipxError(msg)
    if (translated_bool := _UV_BOOL_FLAG_MAP.get(arg)) is not None:
        translated.append(translated_bool)
        return
    flag, separator, attached_value = arg.partition("=")
    if flag in _UV_FORMAT_CONTROL_FLAG_MAP:
        value = attached_value if separator else _next_pip_arg(flag, iterator)
        other_flag = "--only-binary" if flag == "--no-binary" else "--no-binary"
        _update_format_control(flag, value, format_control[flag], format_control[other_flag])
        return
    if (translated_flag := PIP_TO_UV_INDEX_FLAGS.get(flag) or _UV_VALUE_FLAG_MAP.get(flag)) is not None:
        if separator:
            translated.append(f"{translated_flag}={attached_value}")
        else:
            translated.extend([translated_flag, _next_pip_arg(flag, iterator)])
        return
    msg = (
        f"--pip-args contains {redact_url_credentials(arg)!r}, which has no `uv tool run` equivalent.\n"
        "Use `--backend pip` if you need pip-only flags."
    )
    raise PipxError(msg)


def _next_pip_arg(flag: str, iterator: Iterator[str]) -> str:
    try:
        return next(iterator)
    except StopIteration as exc:
        msg = f"Missing value for {flag!r} in --pip-args."
        raise PipxError(msg) from exc


def _update_format_control(flag: str, value: str, target: set[str], other: set[str]) -> None:
    if value.startswith("-") or not all(packages := value.split(",")):
        msg = f"Invalid value for {flag!r} in --pip-args: {redact_url_credentials(value)!r}."
        raise PipxError(msg)
    # The last :all: erases everything before it, including the opposite restriction.
    if (last_all := max((index for index, package in enumerate(packages) if package == ":all:"), default=-1)) >= 0:
        target.clear()
        other.clear()
        target.add(":all:")
        packages = packages[last_all + 1 :]
        if ":none:" not in packages:
            return
    for package in packages:
        if package == ":none:":
            target.clear()
        else:
            name = canonicalize_name(package)
            other.discard(name)
            target.add(name)


def run_script_via_uv_run(script_path: Path, venv_dir: Path, options: RunOptions) -> NoReturn:
    """Run a script through ``uv run``, replacing the current process.

    :param script_path: the script to run, whose inline metadata may declare its requirements.
    :param venv_dir: the directory of the environment, unused by uv.
    :param options: the options of the run.
    :raises PipxError: when venv arguments are given, which ``uv run`` cannot take.
    """
    _reject_venv_args(options.venv_args)
    # uv searches for project config from --project, or else from the script's directory, which another account may own
    cmd: list[str] = [str(resolve_uv_binary()), "run", "--active", "--script", "--project", str(CTX.home)]
    if options.interpreter.python:
        cmd += ["--python", options.interpreter.python]
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
