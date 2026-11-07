from __future__ import annotations

__lazy_modules__ = ["sysconfig"]

import enum
import sys
import sysconfig
from pathlib import PurePosixPath
from typing import Final, NewType


class FetchPythonOptions(enum.StrEnum):
    """When to download a standalone Python: always, only when none is installed, or never.

    :cvar ALWAYS: download a standalone Python every time.
    :cvar MISSING: download a standalone Python only when none is installed.
    :cvar NEVER: never download a standalone Python.
    """

    ALWAYS = "always"
    MISSING = "missing"
    NEVER = "never"


#: Name of the ``.pth`` file that links an environment to the shared libraries.
PIPX_SHARED_PTH: Final[str] = "pipx_shared.pth"
#: Days a temporary environment is reused before it is recreated.
TEMP_VENV_EXPIRATION_THRESHOLD_DAYS: Final[int] = 14
#: Oldest Python version that pipx runs on.
MINIMUM_PYTHON_VERSION: Final[str] = "3.11"
#: Names of the man page section directories.
MAN_SECTIONS: Final[list[str]] = [f"man{i}" for i in range(1, 10)]
# the directories a wheel ships completion scripts in, relative to the data scheme's share/, and the layout bash and
# fish already read from under a user data directory
#: Directories, relative to the share directory, where wheels ship completion scripts.
COMPLETION_SECTIONS: Final[list[PurePosixPath]] = [
    PurePosixPath("bash-completion/completions"),
    PurePosixPath("zsh/site-functions"),
    PurePosixPath("fish/vendor_completions.d"),
]


#: Exit status of a pipx command.
ExitCode = NewType("ExitCode", int)
#: Exit status of a successful command.
EXIT_CODE_OK: Final[ExitCode] = ExitCode(0)
#: Exit status when injecting packages fails.
EXIT_CODE_INJECT_ERROR: Final[ExitCode] = ExitCode(1)
#: Exit status when uninjecting packages fails.
EXIT_CODE_UNINJECT_ERROR: Final[ExitCode] = ExitCode(1)
#: Exit status when listing finds a problem with an environment.
EXIT_CODE_LIST_PROBLEM: Final[ExitCode] = ExitCode(1)
#: Exit status when uninstalling an environment that does not exist.
EXIT_CODE_UNINSTALL_VENV_NONEXISTENT: Final[ExitCode] = ExitCode(1)
#: Exit status when uninstalling fails.
EXIT_CODE_UNINSTALL_ERROR: Final[ExitCode] = ExitCode(1)
#: Exit status when reinstalling an environment that does not exist.
EXIT_CODE_REINSTALL_VENV_NONEXISTENT: Final[ExitCode] = ExitCode(1)
#: Exit status when reinstalling with a Python that cannot be used.
EXIT_CODE_REINSTALL_INVALID_PYTHON: Final[ExitCode] = ExitCode(1)
#: Exit status when the Python executable given to a command is not found.
EXIT_CODE_SPECIFIED_PYTHON_EXECUTABLE_NOT_FOUND: Final[ExitCode] = ExitCode(1)


def _is_mingw() -> bool:
    return sysconfig.get_platform().startswith("mingw")


# not platform.system(): on Windows it queries WMI, adding tens of milliseconds to every startup
#: Whether pipx runs on Windows.
WINDOWS: Final[bool] = sys.platform == "win32"
#: Whether pipx runs on macOS.
MACOS: Final[bool] = sys.platform == "darwin"
#: Whether pipx runs on MinGW, a POSIX-like environment on Windows.
MINGW: Final[bool] = _is_mingw()

__all__ = [
    "COMPLETION_SECTIONS",
    "EXIT_CODE_INJECT_ERROR",
    "EXIT_CODE_LIST_PROBLEM",
    "EXIT_CODE_OK",
    "EXIT_CODE_REINSTALL_INVALID_PYTHON",
    "EXIT_CODE_REINSTALL_VENV_NONEXISTENT",
    "EXIT_CODE_SPECIFIED_PYTHON_EXECUTABLE_NOT_FOUND",
    "EXIT_CODE_UNINJECT_ERROR",
    "EXIT_CODE_UNINSTALL_ERROR",
    "EXIT_CODE_UNINSTALL_VENV_NONEXISTENT",
    "MACOS",
    "MAN_SECTIONS",
    "MINGW",
    "MINIMUM_PYTHON_VERSION",
    "PIPX_SHARED_PTH",
    "TEMP_VENV_EXPIRATION_THRESHOLD_DAYS",
    "WINDOWS",
    "ExitCode",
    "FetchPythonOptions",
]
