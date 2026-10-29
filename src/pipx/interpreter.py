from __future__ import annotations

__lazy_modules__ = [
    "configparser",
    "importlib.util",
    "packaging",
    "pathlib",
    "pipx.self_install",
    "re",
    "shutil",
    "subprocess",
]

import logging
import os
import re
import shutil
import subprocess
import sys
from configparser import ConfigParser
from configparser import Error as ConfigParserError
from functools import cache
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, Final

from packaging import version

from pipx.constants import WINDOWS, FetchPythonOptions
from pipx.self_install import get_environment_value
from pipx.util import PipxError

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

if TYPE_CHECKING:
    DEFAULT_PYTHON: str


def find_python_interpreter(python_version: str, fetch_python: FetchPythonOptions) -> str:
    if fetch_python == FetchPythonOptions.ALWAYS:
        if _has_path_separator(python_version) or Path(python_version).is_file():
            msg = (
                f"--fetch-python={FetchPythonOptions.ALWAYS} requires a Python version "
                f"(e.g. '3.13'), got '{python_version}'."
            )
            raise PipxError(msg)
        return _fetch_standalone_interpreter(python_version)

    # a bare name such as 3.11 must not match a file of that name in the working directory
    if _has_path_separator(python_version) and Path(python_version).is_file():
        return python_version
    # uv reads a bare name such as python3.11 as a version request and may settle on a .venv in a parent directory
    if found := shutil.which(python_version):
        return found

    if not WINDOWS and (python_unix_command := _find_unix_command_python(python_version)):
        return python_unix_command

    try:
        if py_executable := find_py_launcher_python(python_version):
            return py_executable
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        if fetch_python != FetchPythonOptions.MISSING:
            raise InterpreterResolutionError(source="py launcher", version=python_version) from e

    if fetch_python == FetchPythonOptions.MISSING:
        return _fetch_standalone_interpreter(python_version)

    raise InterpreterResolutionError(source="PATH", version=python_version)


def _has_path_separator(python: str) -> bool:
    return os.sep in python or "/" in python


def _fetch_standalone_interpreter(python_version: str) -> str:
    from pipx import standalone_python  # ruff:ignore[import-outside-top-level]  # pulls in http.client, slows startup

    try:
        return standalone_python.download_python_build_standalone(python_version)
    except PipxError as e:
        raise InterpreterResolutionError(source="the python-build-standalone project", version=python_version) from e


class InterpreterResolutionError(PipxError):
    def __init__(self, source: str, version: str) -> None:
        message = (
            f"No executable for the provided Python version '{version}' found in {source}."
            " Check that the provided version is "
        )
        match source:
            case "py launcher":
                message += "listed when running `py --list`."
            case "PATH":
                message += "on your PATH or the file path is valid. "
                if "/" in version:
                    message += "The provided version looks like a path, but no executable was found there."
                elif "python" not in version:
                    message += (
                        "The provided version looks like a version, "
                        "but neither the python command nor the Python Launcher is on PATH."
                    )
            case "the python-build-standalone project":
                message += "listed in https://github.com/astral-sh/python-build-standalone/releases/latest."
            case "PIPX_DEFAULT_PYTHON":
                message += (
                    "on your PATH or the file path is valid. "
                    "Try setting it to an executable name (e.g. python3.10) "
                    "or a full path (e.g. /usr/bin/python3.10)."
                )
        super().__init__(message)


def _find_unix_command_python(python_version: str) -> str | None:
    try:
        parsed_python_version: Final[version.Version] = version.parse(python_version)
    except version.InvalidVersion:
        _LOGGER.info("Invalid Python version: %s", python_version)
        return None

    if (
        parsed_python_version.epoch != 0
        or parsed_python_version.is_devrelease
        or parsed_python_version.is_postrelease
        or parsed_python_version.is_prerelease
    ):
        _LOGGER.info("Unsupported Python version: %s", python_version)
        return None

    # the commands carry at most the minor version, as python3 or python3.12 do
    python_command: Final[str] = f"python{'.'.join(python_version.split('.')[:2])}"

    if not (python_path := shutil.which(python_command)):
        _LOGGER.info("Command `%s` was not found on the system", python_command)
        return None

    if parsed_python_version.micro != 0:
        _LOGGER.warning(
            "The command '%s' located at '%s' will be used. "
            "It may not match the specified version %s at the micro/patch level.",
            python_command,
            python_path,
            python_version,
        )

    return python_path


def find_py_launcher_python(python_version: str | None = None) -> str | None:
    py = shutil.which("py")
    if py and python_version:
        python_semver = python_version
        if python_version.startswith("python"):
            _LOGGER.warning(
                "Removing `python` from the start of the version, as pylauncher just expects the semantic version"
            )
            python_semver = python_semver.lstrip("python")
        # the Unix launcher reads only -X and -X.Y as a version and hands any other flag to the first interpreter its
        # search finds, which can be a .venv in a parent directory; see Action::from_main and venv_path_search in
        # https://github.com/brettcannon/python-launcher/blob/3c9f207c07d5fed612b04dbf2980f67d40aa24b3/src/cli.rs
        if not WINDOWS and not re.fullmatch(r"[0-9]+(\.[0-9]+)?", python_semver):
            return None
        py = subprocess.run(
            [py, f"-{python_semver}", "-c", "import sys; print(sys.executable)"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    return py


def get_default_python_spec() -> str:
    return get_environment_value("PIPX_DEFAULT_PYTHON") or sys.executable


def __getattr__(name: str) -> object:
    if name == "DEFAULT_PYTHON":
        return get_default_python()
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


@cache
def get_default_python() -> str:
    if (python := get_environment_value("PIPX_DEFAULT_PYTHON")) is None:
        return _get_sys_executable()
    return _resolve_python(python)


def _get_sys_executable() -> str:
    if WINDOWS:
        return _find_default_windows_python()
    return str(Path(sys.executable).resolve())


def _find_default_windows_python() -> str:
    # the Windows embeddable distribution ships without venv, so look for a system Python instead; the technique comes
    # from https://github.com/uranusjr/pipx-standalone
    if has_venv():
        return sys.executable
    msg: Final[str] = "No suitable Python found"
    if (python := find_py_launcher_python() or shutil.which("python")) is None:
        raise PipxError(msg)

    if "WindowsApps" not in python:
        return python

    # a Python under WindowsApps may be the Microsoft Store stub, which exits with 9009 or prints no version:
    # https://twitter.com/zooba/status/1212454929379581952
    proc: Final = subprocess.run([python, "-V"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise PipxError(msg)
    return python


def has_venv() -> bool:
    return find_spec("venv") is not None


def _resolve_python(python: str) -> str:
    # a bare name goes to PATH only; testing it as a file first would pick up one sitting in the working directory
    if _has_path_separator(python) and (path := Path(python)).is_file():
        return str(path.resolve())
    if found := shutil.which(python):
        return found
    if not WINDOWS and (found := _find_unix_command_python(python)):
        return found
    raise InterpreterResolutionError(source="PIPX_DEFAULT_PYTHON", version=python)


def recordable_interpreter(python: Path) -> Path | None:
    # an interpreter inside a virtual environment, such as an activated bootstrap's python3, goes away with that
    # environment, and whoever creates the path again decides what install-all runs from a snapshot; the new
    # environment runs on the base interpreter instead
    if not (pyvenv_cfg := python.parent.parent / "pyvenv.cfg").is_file():
        return python
    config: Final[dict[str, str]] = read_pyvenv_cfg(pyvenv_cfg)
    # home keeps the directory the base interpreter ran from, such as a link that survives patch upgrades; executable,
    # resolved and written by venv since 3.11, covers a home without this name, as a macOS framework build has no python
    candidates: Final[list[Path]] = [Path(home) / python.name] if (home := config.get("home")) else []
    if executable := config.get("executable"):
        candidates.append(Path(executable))
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def read_pyvenv_cfg(pyvenv_cfg: Path) -> dict[str, str]:
    config: Final[ConfigParser] = ConfigParser()
    try:
        # pyvenv.cfg has no section header, which ConfigParser requires
        config.read_string(f"[DEFAULT]\n{pyvenv_cfg.read_text(encoding='utf-8')}")
    except (OSError, UnicodeDecodeError, ConfigParserError):
        return {}
    return dict(config["DEFAULT"])


__all__ = [
    "DEFAULT_PYTHON",
    "InterpreterResolutionError",
    "find_py_launcher_python",
    "find_python_interpreter",
    "get_default_python",
    "get_default_python_spec",
    "has_venv",
    "read_pyvenv_cfg",
    "recordable_interpreter",
]
