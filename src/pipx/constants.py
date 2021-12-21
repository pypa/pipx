import os
import sys
from pathlib import Path
from textwrap import dedent
from typing import NewType, Optional

DEFAULT_PIPX_HOME = Path.home() / ".local/pipx"
DEFAULT_PIPX_BIN_DIR = Path.home() / ".local/bin"
PIPX_HOME = Path(os.environ.get("PIPX_HOME", DEFAULT_PIPX_HOME)).resolve()
PIPX_LOCAL_VENVS = PIPX_HOME / "venvs"
PIPX_LOG_DIR = PIPX_HOME / "logs"
DEFAULT_PIPX_SHARED_LIBS = PIPX_HOME / "shared"
PIPX_TRASH_DIR = PIPX_HOME / ".trash"
PIPX_SHARED_LIBS = Path(
    os.environ.get("PIPX_SHARED_LIBS", DEFAULT_PIPX_SHARED_LIBS)
).resolve()
PIPX_SHARED_PTH = "pipx_shared.pth"
LOCAL_BIN_DIR = Path(os.environ.get("PIPX_BIN_DIR", DEFAULT_PIPX_BIN_DIR)).resolve()
PIPX_VENV_CACHEDIR = PIPX_HOME / ".cache"
TEMP_VENV_EXPIRATION_THRESHOLD_DAYS = 14

ExitCode = NewType("ExitCode", int)
# pipx shell exit codes
EXIT_CODE_OK = ExitCode(0)
EXIT_CODE_INJECT_ERROR = ExitCode(1)
EXIT_CODE_INSTALL_VENV_EXISTS = ExitCode(0)
EXIT_CODE_LIST_PROBLEM = ExitCode(1)
EXIT_CODE_UNINSTALL_VENV_NONEXISTENT = ExitCode(1)
EXIT_CODE_UNINSTALL_ERROR = ExitCode(1)
EXIT_CODE_REINSTALL_VENV_NONEXISTENT = ExitCode(1)
EXIT_CODE_REINSTALL_INVALID_PYTHON = ExitCode(1)

pipx_log_file: Optional[Path] = None


def is_windows() -> bool:
    return sys.platform == "win32"


WINDOWS: bool = is_windows()

completion_instructions = dedent(
    """
Add the appropriate command to your shell's config file
so that it is run on startup. You will likely have to restart
or re-login for the autocompletion to start working.

bash:
    eval "$(register-python-argcomplete pipx)"

zsh:
    To activate completions for zsh you need to have
    bashcompinit enabled in zsh:

    autoload -U bashcompinit
    bashcompinit

    Afterwards you can enable completion for pipx:

    eval "$(register-python-argcomplete pipx)"

tcsh:
    eval `register-python-argcomplete --shell tcsh pipx`

fish:
    # Not required to be in the config file, only run once
    register-python-argcomplete --shell fish pipx >~/.config/fish/completions/pipx.fish

"""
)
