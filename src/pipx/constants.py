import enum
import os
import platform
import sys
import sysconfig
from textwrap import dedent
from typing import NewType


# enum.StrEnum is Python 3.11+; pipx supports 3.10.
class FetchPythonOptions(str, enum.Enum):
    ALWAYS = "always"
    MISSING = "missing"
    NEVER = "never"

    def __str__(self) -> str:
        return self.value


PIPX_SHARED_PTH = "pipx_shared.pth"
TEMP_VENV_EXPIRATION_THRESHOLD_DAYS = 14
MINIMUM_PYTHON_VERSION = "3.10"
MAN_SECTIONS = [f"man{i}" for i in range(1, 10)]


def _env_truthy(name: str) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return False
    return raw.strip().lower() not in ("", "0", "false", "no", "off")


FETCH_MISSING_PYTHON = _env_truthy("PIPX_FETCH_MISSING_PYTHON")

_FETCH_PYTHON_VALID = True
try:
    FETCH_PYTHON = FetchPythonOptions(
        os.environ.get("PIPX_FETCH_PYTHON") or (FetchPythonOptions.MISSING if FETCH_MISSING_PYTHON else FetchPythonOptions.NEVER)
    )
except ValueError:
    FETCH_PYTHON = FetchPythonOptions.NEVER
    _FETCH_PYTHON_VALID = False


def validate_fetch_python() -> None:
    from pipx.emojis import hazard
    from pipx.util import PipxError

    if not _FETCH_PYTHON_VALID:
        valid = ", ".join(str(option) for option in FetchPythonOptions)
        raise PipxError(f"PIPX_FETCH_PYTHON must be unset or one of: {valid}.")
    if "PIPX_FETCH_MISSING_PYTHON" in os.environ:
        if "PIPX_FETCH_PYTHON" in os.environ:
            raise PipxError("Setting both PIPX_FETCH_MISSING_PYTHON and PIPX_FETCH_PYTHON is invalid.")
        print(
            f"{hazard} PIPX_FETCH_MISSING_PYTHON is deprecated; "
            f'use PIPX_FETCH_PYTHON="{FetchPythonOptions.MISSING}" instead.',
            file=sys.stderr,
        )


ExitCode = NewType("ExitCode", int)
# pipx shell exit codes
EXIT_CODE_OK = ExitCode(0)
EXIT_CODE_INJECT_ERROR = ExitCode(1)
EXIT_CODE_UNINJECT_ERROR = ExitCode(1)
EXIT_CODE_INSTALL_VENV_EXISTS = ExitCode(0)
EXIT_CODE_LIST_PROBLEM = ExitCode(1)
EXIT_CODE_UNINSTALL_VENV_NONEXISTENT = ExitCode(1)
EXIT_CODE_UNINSTALL_ERROR = ExitCode(1)
EXIT_CODE_REINSTALL_VENV_NONEXISTENT = ExitCode(1)
EXIT_CODE_REINSTALL_INVALID_PYTHON = ExitCode(1)
EXIT_CODE_SPECIFIED_PYTHON_EXECUTABLE_NOT_FOUND = ExitCode(1)


def is_windows() -> bool:
    return platform.system() == "Windows"


def is_macos() -> bool:
    return platform.system() == "Darwin"


def is_linux() -> bool:
    return platform.system() == "Linux"


def is_mingw() -> bool:
    return sysconfig.get_platform().startswith("mingw")


WINDOWS: bool = is_windows()
MACOS: bool = is_macos()
LINUX: bool = is_linux()
MINGW: bool = is_mingw()

completion_instructions = dedent(
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
