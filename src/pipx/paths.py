import os
from pathlib import Path
from typing import Optional, Union

from platformdirs import user_cache_path, user_data_path, user_log_path

DEFAULT_PIPX_HOME = user_data_path("pipx")
FALLBACK_PIPX_HOME = Path.home() / ".local/pipx"
DEFAULT_PIPX_BIN_DIR = Path.home() / ".local/bin"
DEFAULT_PIPX_MAN_DIR = Path.home() / ".local/share/man"
DEFAULT_PIPX_GLOBAL_HOME = "/opt/pipx"
DEFAULT_PIPX_GLOBAL_BIN_DIR = "/usr/local/bin"
DEFAULT_PIPX_GLOBAL_MAN_DIR = "/usr/local/share/man"


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
    _fallback_home: Path = Path.home() / ".local/pipx"
    _home_exists: bool = _base_home is not None or _fallback_home.exists()
    log_file: Optional[Path] = None

    @property
    def venvs(self) -> Path:
        return self.home / "venvs"

    @property
    def logs(self) -> Path:
        if self._home_exists:
            return self.home / "logs"
        return user_log_path("pipx")

    @property
    def trash(self) -> Path:
        if self._home_exists:
            return self.home / ".trash"
        return self.home / "trash"

    @property
    def venv_cache(self) -> Path:
        if self._home_exists:
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
        elif self._fallback_home.exists():
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
        self._home_exists = self._base_home is not None or self._fallback_home.exists()

    def make_global(self) -> None:
        self._base_home = get_expanded_environ("PIPX_GLOBAL_HOME") or DEFAULT_PIPX_GLOBAL_HOME
        self._base_bin = get_expanded_environ("PIPX_GLOBAL_BIN_DIR") or DEFAULT_PIPX_GLOBAL_BIN_DIR
        self._base_man = get_expanded_environ("PIPX_GLOBAL_MAN_DIR") or DEFAULT_PIPX_GLOBAL_MAN_DIR
        self._home_exists = self._base_home is not None or self._fallback_home.exists()

    @property
    def standalone_python_cachedir(self) -> Path:
        return self.home / "py"


ctx = _PathContext()
