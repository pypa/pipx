from __future__ import annotations

__lazy_modules__ = ["sysconfig"]

import enum
import os
import sys
import sysconfig
from pathlib import PurePosixPath
from textwrap import dedent
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


FETCH_MISSING_PYTHON_RAW: Final[str | None] = os.environ.get("PIPX_FETCH_MISSING_PYTHON")
FETCH_PYTHON_RAW: Final[str | None] = os.environ.get("PIPX_FETCH_PYTHON")


def compute_fetch_python(missing_raw: str | None, python_raw: str | None) -> tuple[FetchPythonOptions, bool]:
    fetch_missing: Final[bool] = (missing_raw or "").strip().lower() not in {"", "0", "false", "f", "no", "n", "off"}
    raw: Final[str] = python_raw or (
        FetchPythonOptions.MISSING.value if fetch_missing else FetchPythonOptions.NEVER.value
    )
    try:
        return FetchPythonOptions(raw), False
    except ValueError:
        return FetchPythonOptions.NEVER, True


FETCH_PYTHON, FETCH_PYTHON_INVALID = compute_fetch_python(FETCH_MISSING_PYTHON_RAW, FETCH_PYTHON_RAW)

COOLDOWN_RAW: Final[str | None] = os.environ.get("PIPX_COOLDOWN")


def compute_cooldown(raw: str | None) -> tuple[int | None, bool]:
    if raw is None or not (stripped := raw.strip()):
        return None, False
    try:
        days: Final[int] = int(stripped)
    except ValueError:
        return None, True
    return (days, False) if days >= 0 else (None, True)


COOLDOWN, COOLDOWN_INVALID = compute_cooldown(COOLDOWN_RAW)


MAX_LOGS_RAW: Final[str | None] = os.environ.get("PIPX_MAX_LOGS")


def compute_max_logs(raw: str | None) -> tuple[int, bool]:
    if raw is None or not (stripped := raw.strip()):
        return 10, False
    try:
        logs: Final[int] = int(stripped)
    except ValueError:
        return 10, True
    return (logs, False) if logs >= 0 else (10, True)


MAX_LOGS_INVALID: Final[bool] = compute_max_logs(MAX_LOGS_RAW)[1]


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

COMPLETION_INSTRUCTIONS: Final[str] = dedent(
    """
If you encountered register-python-argcomplete command not found error,
or if you are using zipapp, run

    pipx install argcomplete

before running any of the following commands.

Add the appropriate command to your shell's config file
so that it is run on startup. You will likely have to restart
or re-login for the autocompletion to start working.

bash:
    eval "$(register-python-argcomplete pipx)"

zsh:
    To activate completions in zsh, first make sure compinit is marked for
    autoload and run autoload:

    autoload -U compinit && compinit

    Afterwards you can enable completions for pipx:

    eval "$(register-python-argcomplete pipx)"

    NOTE: If your version of argcomplete is earlier than v3, you may need to
    have bashcompinit enabled in zsh by running:

    autoload -U bashcompinit
    bashcompinit


tcsh:
    eval `register-python-argcomplete --shell tcsh pipx`

fish:
    # Not required to be in the config file, only run once
    register-python-argcomplete --shell fish pipx >~/.config/fish/completions/pipx.fish

"""
)


__all__ = [
    "COMPLETION_INSTRUCTIONS",
    "COMPLETION_SECTIONS",
    "COOLDOWN",
    "COOLDOWN_INVALID",
    "COOLDOWN_RAW",
    "EXIT_CODE_INJECT_ERROR",
    "EXIT_CODE_LIST_PROBLEM",
    "EXIT_CODE_OK",
    "EXIT_CODE_REINSTALL_INVALID_PYTHON",
    "EXIT_CODE_REINSTALL_VENV_NONEXISTENT",
    "EXIT_CODE_SPECIFIED_PYTHON_EXECUTABLE_NOT_FOUND",
    "EXIT_CODE_UNINJECT_ERROR",
    "EXIT_CODE_UNINSTALL_ERROR",
    "EXIT_CODE_UNINSTALL_VENV_NONEXISTENT",
    "FETCH_MISSING_PYTHON_RAW",
    "FETCH_PYTHON",
    "FETCH_PYTHON_INVALID",
    "FETCH_PYTHON_RAW",
    "MACOS",
    "MAN_SECTIONS",
    "MAX_LOGS_INVALID",
    "MAX_LOGS_RAW",
    "MINGW",
    "MINIMUM_PYTHON_VERSION",
    "PIPX_SHARED_PTH",
    "TEMP_VENV_EXPIRATION_THRESHOLD_DAYS",
    "WINDOWS",
    "ExitCode",
    "FetchPythonOptions",
    "compute_cooldown",
    "compute_fetch_python",
    "compute_max_logs",
]
