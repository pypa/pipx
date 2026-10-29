from __future__ import annotations

__lazy_modules__ = ["pipx.self_install", "pipx.wrap", "typing"]

import logging
from functools import cached_property
from pathlib import Path
from typing import Final

from platformdirs import user_cache_path, user_data_path, user_log_path

from pipx.constants import WINDOWS
from pipx.self_install import DEFAULT_PIPX_GLOBAL_HOME, get_environment_value
from pipx.wrap import pipx_wrap

DEFAULT_PIPX_HOME: Final[Path] = user_data_path("pipx")
FALLBACK_PIPX_HOMES: Final[list[Path]] = [Path.home() / ".local/pipx", *([Path.home() / "pipx"] if WINDOWS else [])]

DEFAULT_PIPX_BIN_DIR: Final[Path] = Path.home() / ".local/bin"
DEFAULT_PIPX_MAN_DIR: Final[Path] = Path.home() / ".local/share/man"
DEFAULT_PIPX_GLOBAL_BIN_DIR: Final[Path] = Path("/usr/local/bin")
DEFAULT_PIPX_GLOBAL_MAN_DIR: Final[Path] = Path("/usr/local/share/man")

# tests point these at temporary directories so no test touches the real pipx locations
OVERRIDE_PIPX_HOME: Path | None = None
OVERRIDE_PIPX_BIN_DIR: Path | None = None
OVERRIDE_PIPX_MAN_DIR: Path | None = None
OVERRIDE_PIPX_COMPLETION_DIR: Path | None = None
OVERRIDE_PIPX_SHARED_LIBS: Path | None = None
OVERRIDE_PIPX_GLOBAL_HOME: Path | None = None
OVERRIDE_PIPX_GLOBAL_BIN_DIR: Path | None = None
OVERRIDE_PIPX_GLOBAL_MAN_DIR: Path | None = None
OVERRIDE_PIPX_GLOBAL_COMPLETION_DIR: Path | None = None
OVERRIDE_PIPX_GLOBAL_SHARED_LIBS: Path | None = None

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


class _PathContext:
    _base_home: Path | None
    _default_home: Path
    _base_bin: Path | None
    _default_bin: Path
    _base_man: Path | None
    _default_man: Path
    _base_completion: Path | None
    _default_completion: Path
    _default_log: Path
    _default_cache: Path
    _default_trash: Path
    _base_shared_libs: Path | None
    _fallback_home: Path | None
    _home_exists: bool
    log_file: Path | None = None

    def __init__(self) -> None:
        self.make_local()

    def make_local(self) -> None:
        self._base_home = OVERRIDE_PIPX_HOME or get_expanded_environ("PIPX_HOME")
        self._default_home = DEFAULT_PIPX_HOME
        self._base_bin = OVERRIDE_PIPX_BIN_DIR or get_expanded_environ("PIPX_BIN_DIR")
        self._default_bin = DEFAULT_PIPX_BIN_DIR
        self._base_man = OVERRIDE_PIPX_MAN_DIR or get_expanded_environ("PIPX_MAN_DIR")
        self._default_man = DEFAULT_PIPX_MAN_DIR
        self._base_completion = OVERRIDE_PIPX_COMPLETION_DIR or get_expanded_environ("PIPX_COMPLETION_DIR")
        self._default_completion = Path.home() / ".local/share"
        self._base_shared_libs = OVERRIDE_PIPX_SHARED_LIBS or get_expanded_environ("PIPX_SHARED_LIBS")
        self._default_log = user_log_path("pipx")
        self._default_cache = user_cache_path("pipx")
        self._default_trash = self._default_home / "trash"
        self._fallback_home = next((fallback for fallback in FALLBACK_PIPX_HOMES if fallback.exists()), None)
        self._home_exists = self._base_home is not None or any(fallback.exists() for fallback in FALLBACK_PIPX_HOMES)
        self._clear_cached_paths()

    def _clear_cached_paths(self) -> None:
        for attribute in ("bin_dir", "completion_dir", "home", "man_dir", "shared_libs"):
            self.__dict__.pop(attribute, None)

    def make_global(self) -> None:
        self._base_home = OVERRIDE_PIPX_GLOBAL_HOME or get_expanded_environ("PIPX_GLOBAL_HOME")
        self._default_home = DEFAULT_PIPX_GLOBAL_HOME
        self._base_bin = OVERRIDE_PIPX_GLOBAL_BIN_DIR or get_expanded_environ("PIPX_GLOBAL_BIN_DIR")
        self._default_bin = DEFAULT_PIPX_GLOBAL_BIN_DIR
        self._base_man = OVERRIDE_PIPX_GLOBAL_MAN_DIR or get_expanded_environ("PIPX_GLOBAL_MAN_DIR")
        self._default_man = DEFAULT_PIPX_GLOBAL_MAN_DIR
        self._base_completion = OVERRIDE_PIPX_GLOBAL_COMPLETION_DIR or get_expanded_environ(
            "PIPX_GLOBAL_COMPLETION_DIR"
        )
        self._default_completion = Path("/usr/local/share")
        self._default_log = self._default_home / "logs"
        self._default_cache = self._default_home / ".cache"
        self._default_trash = self._default_home / "trash"
        self._base_shared_libs = OVERRIDE_PIPX_GLOBAL_SHARED_LIBS
        self._fallback_home = None
        self._home_exists = self._base_home is not None
        self._clear_cached_paths()

    @property
    def venvs(self) -> Path:
        return self.home / "venvs"

    @cached_property
    def home(self) -> Path:
        return (self._base_home or self._fallback_home or self._default_home).absolute()

    @property
    def logs(self) -> Path:
        # a legacy home keeps holding the venvs, yet its logs and cache belong in the platform locations, so only an
        # explicit PIPX_HOME pulls them back under the home
        return self.home / "logs" if self._base_home else self._default_log

    @property
    def venv_cache(self) -> Path:
        return self.home / ".cache" if self._base_home else self._default_cache

    @property
    def trash(self) -> Path:
        # renaming into the trash has to stay on one filesystem, so it follows the venvs under the home
        return self.home / ".trash" if self._home_exists else self._default_trash

    @cached_property
    def bin_dir(self) -> Path:
        return (self._base_bin or self._default_bin).resolve()

    @cached_property
    def man_dir(self) -> Path:
        return (self._base_man or self._default_man).resolve()

    @cached_property
    def completion_dir(self) -> Path:
        return (self._base_completion or self._default_completion).resolve()

    @cached_property
    def shared_libs(self) -> Path:
        return (self._base_shared_libs or self.home / "shared").resolve()

    @property
    def standalone_python_cachedir(self) -> Path:
        return self.home / "py"

    def log_warnings(self) -> None:
        if self._fallback_home is not None and self._fallback_home.exists() and self.home != self._fallback_home:
            _LOGGER.info(
                pipx_wrap(
                    (
                        f"Both a specific pipx home folder ({self.home}) and the fallback "
                        f"pipx home folder ({self._fallback_home}) exist. If you are done migrating from the "
                        "fallback to the new location, it is safe to delete the fallback location."
                    ),
                    subsequent_indent=" " * 4,
                )
            )


def get_expanded_environ(env_name: str) -> Path | None:
    return Path(value).expanduser().absolute() if (value := get_environment_value(env_name)) else None


CTX: Final[_PathContext] = _PathContext()


__all__ = [
    "CTX",
    "DEFAULT_PIPX_BIN_DIR",
    "DEFAULT_PIPX_GLOBAL_BIN_DIR",
    "DEFAULT_PIPX_GLOBAL_HOME",
    "DEFAULT_PIPX_GLOBAL_MAN_DIR",
    "DEFAULT_PIPX_HOME",
    "DEFAULT_PIPX_MAN_DIR",
    "OVERRIDE_PIPX_BIN_DIR",
    "OVERRIDE_PIPX_COMPLETION_DIR",
    "OVERRIDE_PIPX_GLOBAL_BIN_DIR",
    "OVERRIDE_PIPX_GLOBAL_COMPLETION_DIR",
    "OVERRIDE_PIPX_GLOBAL_HOME",
    "OVERRIDE_PIPX_GLOBAL_MAN_DIR",
    "OVERRIDE_PIPX_GLOBAL_SHARED_LIBS",
    "OVERRIDE_PIPX_HOME",
    "OVERRIDE_PIPX_MAN_DIR",
    "OVERRIDE_PIPX_SHARED_LIBS",
    "get_expanded_environ",
]
