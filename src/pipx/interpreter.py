import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from packaging import version

from pipx.constants import FETCH_MISSING_PYTHON, WINDOWS
from pipx.standalone_python import download_python_build_standalone
from pipx.util import PipxError

logger = logging.getLogger(__name__)


def has_venv() -> bool:
    try:
        import venv  # noqa: F401
    except ImportError:
        return False
    return True


class InterpreterResolutionError(PipxError):
    def __init__(self, source: str, version: str, wrap_message: bool = True):
        self.source = source
        self.version = version
        potentially_path = "/" in version
        potentially_pylauncher = "python" not in version and not potentially_path

        message = (
            f"No executable for the provided Python version '{version}' found in {source}."
            " Please make sure the provided version is "
        )
        if source == "py launcher":
            message += "listed when running `py --list`."
        if source == "PATH":
            message += "on your PATH or the file path is valid. "
            if potentially_path:
                message += "The provided version looks like a path, but no executable was found there."
            if potentially_pylauncher:
                message += (
                    "The provided version looks like a version, "
                    "but both the python command and the Python Launcher were not found on PATH."
                )
        if source == "the python-build-standalone project":
            message += "listed in https://github.com/indygreg/python-build-standalone/releases/latest."
        super().__init__(message, wrap_message)


def find_unix_command_python(python_version: str) -> Optional[str]:
    try:
        parsed_python_version = version.parse(python_version)
    except version.InvalidVersion:
        logger.info(f"Invalid Python version: {python_version}")
        return None

    if (
        parsed_python_version.epoch != 0
        or parsed_python_version.is_devrelease
        or parsed_python_version.is_postrelease
        or parsed_python_version.is_prerelease
    ):
        logger.info(f"Unsupported Python version: {python_version}")
        return None

    # Python command could be `python3` or `python3.x` without micro version component
    python_command = f"python{'.'.join(python_version.split('.')[:2])}"

    python_path = shutil.which(python_command)
    if not python_path:
        logger.info(f"Command `{python_command}` was not found on the system")
        return None

    if parsed_python_version.micro != 0:
        logger.warning(
            f"The command '{python_command}' located at '{python_path}' will be used. "
            f"It may not match the specified version {python_version} at the micro/patch level."
        )

    return python_path


def find_python_interpreter(python_version: str, fetch_missing_python: bool = False) -> str:
    if Path(python_version).is_file() or shutil.which(python_version):
        return python_version

    if not WINDOWS:
        python_unix_command = find_unix_command_python(python_version)
        if python_unix_command:
            return python_unix_command

    try:
        py_executable = find_py_launcher_python(python_version)
        if py_executable:
            return py_executable
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise InterpreterResolutionError(source="py launcher", version=python_version) from e

    if fetch_missing_python or FETCH_MISSING_PYTHON:
        try:
            return download_python_build_standalone(python_version)
        except PipxError as e:
            raise InterpreterResolutionError(source="the python-build-standalone project", version=python_version) from e

    raise InterpreterResolutionError(source="PATH", version=python_version)


# The following code was copied from https://github.com/uranusjr/pipx-standalone
# which uses the same technique to build a completely standalone pipx
# distribution.
#
# If we are running under the Windows embeddable distribution,
# venv isn't available (and we probably don't want to use the
# embeddable distribution as our applications' base Python anyway)
# so we try to locate the system Python and use that instead.


def find_py_launcher_python(python_version: Optional[str] = None) -> Optional[str]:
    py = shutil.which("py")
    if py and python_version:
        python_semver = python_version
        if python_version.startswith("python"):
            logger.warning(
                "Removing `python` from the start of the version, as pylauncher just expects the semantic version"
            )
            python_semver = python_semver.lstrip("python")
        py = subprocess.run(
            [py, f"-{python_semver}", "-c", "import sys; print(sys.executable)"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    return py


def _find_default_windows_python() -> str:
    if has_venv():
        return sys.executable
    python = find_py_launcher_python() or shutil.which("python")

    if python is None:
        raise PipxError("No suitable Python found")

    # If the path contains "WindowsApps", it's the store python
    if "WindowsApps" not in python:
        return python

    # Special treatment to detect Windows Store stub.
    # https://twitter.com/zooba/status/1212454929379581952

    proc = subprocess.run([python, "-V"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    if proc.returncode != 0:
        # Cover the 9009 return code pre-emptively.
        raise PipxError("No suitable Python found")
    if not proc.stdout.strip():
        # A real Python should print version, Windows Store stub won't.
        raise PipxError("No suitable Python found")
    return python  # This executable seems to work.


def _get_sys_executable() -> str:
    if WINDOWS:
        return _find_default_windows_python()
    else:
        return str(Path(sys.executable).resolve())


def _get_absolute_python_interpreter(env_python: str) -> str:
    which_python = shutil.which(env_python)
    if not which_python:
        raise PipxError(f"Default python interpreter '{env_python}' is invalid.")
    return which_python


env_default_python = os.environ.get("PIPX_DEFAULT_PYTHON")

if not env_default_python:
    DEFAULT_PYTHON = _get_sys_executable()
else:
    DEFAULT_PYTHON = _get_absolute_python_interpreter(env_default_python)
