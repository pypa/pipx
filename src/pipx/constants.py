from __future__ import annotations

__lazy_modules__ = ["sysconfig"]

import enum
import sys
import sysconfig
from pathlib import PurePosixPath
from typing import Final, NewType


class FetchPythonOptions(enum.StrEnum):
    ALWAYS = "always"
    MISSING = "missing"
    NEVER = "never"


PIPX_SHARED_PTH: Final[str] = "pipx_shared.pth"
TEMP_VENV_EXPIRATION_THRESHOLD_DAYS: Final[int] = 14
MINIMUM_PYTHON_VERSION: Final[str] = "3.11"
MAN_SECTIONS: Final[list[str]] = [f"man{i}" for i in range(1, 10)]
# the directories a wheel ships completion scripts in, relative to the data scheme's share/, and the layout bash and
# fish already read from under a user data directory
COMPLETION_SECTIONS: Final[list[PurePosixPath]] = [
    PurePosixPath("bash-completion/completions"),
    PurePosixPath("zsh/site-functions"),
    PurePosixPath("fish/vendor_completions.d"),
]


ExitCode = NewType("ExitCode", int)
EXIT_CODE_OK: Final[ExitCode] = ExitCode(0)
EXIT_CODE_INJECT_ERROR: Final[ExitCode] = ExitCode(1)
EXIT_CODE_UNINJECT_ERROR: Final[ExitCode] = ExitCode(1)
EXIT_CODE_LIST_PROBLEM: Final[ExitCode] = ExitCode(1)
EXIT_CODE_UNINSTALL_VENV_NONEXISTENT: Final[ExitCode] = ExitCode(1)
EXIT_CODE_UNINSTALL_ERROR: Final[ExitCode] = ExitCode(1)
EXIT_CODE_REINSTALL_VENV_NONEXISTENT: Final[ExitCode] = ExitCode(1)
EXIT_CODE_REINSTALL_INVALID_PYTHON: Final[ExitCode] = ExitCode(1)
EXIT_CODE_SPECIFIED_PYTHON_EXECUTABLE_NOT_FOUND: Final[ExitCode] = ExitCode(1)


def _is_mingw() -> bool:
    return sysconfig.get_platform().startswith("mingw")


# not platform.system(): on Windows it queries WMI, adding tens of milliseconds to every startup
WINDOWS: Final[bool] = sys.platform == "win32"
MACOS: Final[bool] = sys.platform == "darwin"
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
