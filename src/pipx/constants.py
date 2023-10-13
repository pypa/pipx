import os
import sys
import sysconfig
from pathlib import Path
from textwrap import dedent
from typing import NewType, Optional

from platformdirs import user_cache_path, user_data_path, user_log_path

DEFAULT_PIPX_HOME = user_data_path("pipx")
FALLBACK_PIPX_HOME = Path.home() / ".local/pipx"
DEFAULT_PIPX_BIN_DIR = Path.home() / ".local/bin"
DEFAULT_PIPX_GLOBAL_BIN_DIR = "/usr/local/bin"
DEFAULT_PIPX_GLOBAL_HOME = "/opt/pipx"

PIPX_SHARED_PTH = "pipx_shared.pth"
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

pipx_log_file: Optional[Path] = None


class PIPXDirs:
    _base_home = os.environ.get("PIPX_HOME")
    _base_bin = os.environ.get("PIPX_BIN_DIR")
    _base_shared_libs = os.environ.get("PIPX_SHARED_LIBS")
    _fallback_home = Path.home() / ".local/pipx"
    _in_home = _base_home is not None or _fallback_home.exists()

    @property
    def LOCAL_VENVS(self) -> Path:
        return self.HOME / "venvs"

    @property
    def LOG_DIR(self) -> Path:
        if self._in_home:
            return self.HOME / "logs"
        return user_log_path("pipx")

    @property
    def TRASH_DIR(self) -> Path:
        if self._in_home:
            return self.HOME / ".trash"
        return self.HOME / "trash"

    @property
    def VENV_CACHEDIR(self) -> Path:
        if self._in_home:
            return self.HOME / ".cache"
        return user_cache_path("pipx")

    @property
    def BIN_DIR(self) -> Path:
        return Path(self._base_bin or DEFAULT_PIPX_BIN_DIR).resolve()

    @property
    def HOME(self) -> Path:
        if self._base_home:
            home = Path(self._base_home)
        elif self._fallback_home.exists():
            home = self._fallback_home
        else:
            home = Path(DEFAULT_PIPX_HOME)
        return home.resolve()

    @property
    def DEFAULT_SHARED_LIBS(self) -> Path:
        return self.HOME / "shared"

    @property
    def SHARED_LIBS(self) -> Path:
        return Path(self._base_shared_libs or self.DEFAULT_SHARED_LIBS).resolve()

    def make_global(self) -> None:
        self._base_home = DEFAULT_PIPX_GLOBAL_HOME
        self._base_bin = DEFAULT_PIPX_GLOBAL_BIN_DIR


PIPX_DIRS = PIPXDirs()


def is_windows() -> bool:
    return sys.platform == "win32"


def is_mingw() -> bool:
    return sysconfig.get_platform().startswith("mingw")


WINDOWS: bool = is_windows()
MINGW: bool = is_mingw()

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
