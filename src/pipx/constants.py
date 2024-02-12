import os
import sys
import sysconfig
from pathlib import Path
from textwrap import dedent
from typing import NewType, Optional

from platformdirs import user_cache_path, user_data_path, user_log_path


def load_dir_from_environ(dir_name: str, default: Path) -> Path:
    env = os.environ.get(dir_name, default)
    return Path(os.path.expanduser(env)).resolve()


DEFAULT_PIPX_HOME = user_data_path("pipx")
FALLBACK_PIPX_HOME = Path.home() / ".local/pipx"
DEFAULT_PIPX_BIN_DIR = Path.home() / ".local/bin"
DEFAULT_PIPX_MAN_DIR = Path.home() / ".local/share/man"
MAN_SECTIONS = ["man%d" % i for i in range(1, 10)]

if FALLBACK_PIPX_HOME.exists() or os.environ.get("PIPX_HOME") is not None:
    PIPX_HOME = load_dir_from_environ("PIPX_HOME", FALLBACK_PIPX_HOME)
    PIPX_LOCAL_VENVS = PIPX_HOME / "venvs"
    PIPX_STANDALONE_PYTHON_CACHEDIR = PIPX_HOME / "py"
    PIPX_LOG_DIR = PIPX_HOME / "logs"
    DEFAULT_PIPX_SHARED_LIBS = PIPX_HOME / "shared"
    PIPX_TRASH_DIR = PIPX_HOME / ".trash"
    PIPX_VENV_CACHEDIR = PIPX_HOME / ".cache"
else:
    PIPX_HOME = DEFAULT_PIPX_HOME
    PIPX_LOCAL_VENVS = PIPX_HOME / "venvs"
    PIPX_STANDALONE_PYTHON_CACHEDIR = PIPX_HOME / "py"
    PIPX_LOG_DIR = user_log_path("pipx")
    DEFAULT_PIPX_SHARED_LIBS = PIPX_HOME / "shared"
    PIPX_TRASH_DIR = PIPX_HOME / "trash"
    PIPX_VENV_CACHEDIR = user_cache_path("pipx")

PIPX_SHARED_LIBS = load_dir_from_environ("PIPX_SHARED_LIBS", DEFAULT_PIPX_SHARED_LIBS)
PIPX_SHARED_PTH = "pipx_shared.pth"
LOCAL_BIN_DIR = load_dir_from_environ("PIPX_BIN_DIR", DEFAULT_PIPX_BIN_DIR)
LOCAL_MAN_DIR = load_dir_from_environ("PIPX_MAN_DIR", DEFAULT_PIPX_MAN_DIR)
FETCH_MISSING_PYTHON = os.environ.get("PIPX_FETCH_MISSING_PYTHON", False)
TEMP_VENV_EXPIRATION_THRESHOLD_DAYS = 14
MINIMUM_PYTHON_VERSION = "3.8"

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

pipx_log_file: Optional[Path] = None


def is_windows() -> bool:
    return sys.platform == "win32"


def is_mingw() -> bool:
    return sysconfig.get_platform().startswith("mingw")


WINDOWS: bool = is_windows()
MINGW: bool = is_mingw()

completion_instructions = dedent(
    """
If you are using zipapp, run `pipx install argcomplete` before
running any of the following commands.

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
