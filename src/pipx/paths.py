import logging
import os
from pathlib import Path
from typing import List, Optional, Union

from platformdirs import user_cache_path, user_data_path, user_log_path

from pipx.constants import LINUX, WINDOWS
from pipx.emojis import hazard
from pipx.util import pipx_wrap

if LINUX:
    DEFAULT_PIPX_HOME = user_data_path("pipx")
    FALLBACK_PIPX_HOMES = [Path.home() / ".local/pipx"]
elif WINDOWS:
    DEFAULT_PIPX_HOME = Path.home() / "pipx"
    FALLBACK_PIPX_HOMES = [Path.home() / ".local/pipx", user_data_path("pipx")]
else:
    DEFAULT_PIPX_HOME = Path.home() / ".local/pipx"
    FALLBACK_PIPX_HOMES = [user_data_path("pipx")]

DEFAULT_PIPX_BIN_DIR = Path.home() / ".local/bin"
DEFAULT_PIPX_MAN_DIR = Path.home() / ".local/share/man"
DEFAULT_PIPX_GLOBAL_HOME = "/opt/pipx"
DEFAULT_PIPX_GLOBAL_BIN_DIR = "/usr/local/bin"
DEFAULT_PIPX_GLOBAL_MAN_DIR = "/usr/local/share/man"


logger = logging.getLogger(__name__)


def get_expanded_environ(env_name: str) -> Optional[Path]:
    val = os.environ.get(env_name)
    if val is not None:
        return Path(val).expanduser().resolve()
    return val


class _PathContext:
    _base_home: Optional[Union[Path, str]] = get_expanded_environ("PIPX_HOME")
    _base_bin: Optional[Union[Path, str]] = get_expanded_environ("PIPX_BIN_DIR")
    _base_man: Optional[Union[Path, str]] = get_expanded_environ("PIPX_MAN_DIR")
    _base_shared_libs: Optional[Union[Path, str]] = get_expanded_environ("PIPX_SHARED_LIBS")
    _fallback_homes: List[Path] = FALLBACK_PIPX_HOMES
    _fallback_home: Optional[Path] = next(iter([fallback for fallback in _fallback_homes if fallback.exists()]), None)
    _home_exists: bool = _base_home is not None or any(fallback.exists() for fallback in _fallback_homes)
    log_file: Optional[Path] = None

    @property
    def venvs(self) -> Path:
        return self.home / "venvs"

    @property
    def logs(self) -> Path:
        if self._home_exists or not LINUX:
            return self.home / "logs"
        return user_log_path("pipx")

    @property
    def trash(self) -> Path:
        if self._home_exists:
            return self.home / ".trash"
        return self.home / "trash"

    @property
    def venv_cache(self) -> Path:
        if self._home_exists or not LINUX:
            return self.home / ".cache"
        return user_cache_path("pipx")

    @property
    def bin_dir(self) -> Path:
        return Path(self._base_bin or DEFAULT_PIPX_BIN_DIR).resolve()

    @property
    def man_dir(self) -> Path:
        return Path(self._base_man or DEFAULT_PIPX_MAN_DIR).resolve()

    @property
    def home(self) -> Path:
        if self._base_home:
            home = Path(self._base_home)
        elif self._fallback_home:
            home = self._fallback_home
        else:
            home = Path(DEFAULT_PIPX_HOME)
        return home.resolve()

    @property
    def shared_libs(self) -> Path:
        return Path(self._base_shared_libs or self.home / "shared").resolve()

    def make_local(self) -> None:
        self._base_home = get_expanded_environ("PIPX_HOME")
        self._base_bin = get_expanded_environ("PIPX_BIN_DIR")
        self._base_man = get_expanded_environ("PIPX_MAN_DIR")
        self._home_exists = self._base_home is not None or any(fallback.exists() for fallback in self._fallback_homes)

    def make_global(self) -> None:
        self._base_home = get_expanded_environ("PIPX_GLOBAL_HOME") or DEFAULT_PIPX_GLOBAL_HOME
        self._base_bin = get_expanded_environ("PIPX_GLOBAL_BIN_DIR") or DEFAULT_PIPX_GLOBAL_BIN_DIR
        self._base_man = get_expanded_environ("PIPX_GLOBAL_MAN_DIR") or DEFAULT_PIPX_GLOBAL_MAN_DIR
        self._home_exists = self._base_home is not None or any(fallback.exists() for fallback in self._fallback_homes)

    @property
    def standalone_python_cachedir(self) -> Path:
        return self.home / "py"

    def log_warnings(self):
        if " " in str(self.home):
            logger.warning(
                pipx_wrap(
                    (
                        f"{hazard} Found a space in the home path. We heavily discourage this, due to "
                        "multiple incompatibilities. Please check our docs for more information on this, "
                        "as well as some pointers on how to migrate to a different home path."
                    ),
                    subsequent_indent=" " * 4,
                )
            )

        fallback_home_exists = self._fallback_home is not None and self._fallback_home.exists()
        specific_home_exists = self.home != self._fallback_home
        if fallback_home_exists and specific_home_exists:
            logger.info(
                pipx_wrap(
                    (
                        f"Both a specific pipx home folder ({self.home}) and the fallback "
                        f"pipx home folder ({self._fallback_home}) exist. If you are done migrating from the"
                        "fallback to the new location, it is safe to delete the fallback location."
                    ),
                    subsequent_indent=" " * 4,
                )
            )


ctx = _PathContext()
ctx.log_warnings()
