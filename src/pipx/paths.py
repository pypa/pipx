import logging
import os
from functools import cached_property
from pathlib import Path
from typing import Final

from platformdirs import user_cache_path, user_data_path, user_log_path

from pipx.constants import LINUX, WINDOWS
from pipx.emojis import hazard, strtobool
from pipx.self_install import get_environment_value
from pipx.wrap import pipx_wrap

if LINUX:
    DEFAULT_PIPX_HOME = Path(user_data_path("pipx"))
    FALLBACK_PIPX_HOMES = [Path.home() / ".local/pipx"]
elif WINDOWS:
    DEFAULT_PIPX_HOME = Path.home() / "pipx"
    FALLBACK_PIPX_HOMES = [Path.home() / ".local/pipx", Path(user_data_path("pipx"))]
else:
    DEFAULT_PIPX_HOME = Path.home() / ".local/pipx"
    FALLBACK_PIPX_HOMES = [Path(user_data_path("pipx"))]

DEFAULT_PIPX_BIN_DIR: Final[Path] = Path.home() / ".local/bin"
DEFAULT_PIPX_MAN_DIR: Final[Path] = Path.home() / ".local/share/man"
DEFAULT_PIPX_GLOBAL_HOME: Final[Path] = Path("/opt/pipx")
DEFAULT_PIPX_GLOBAL_BIN_DIR: Final[Path] = Path("/usr/local/bin")
DEFAULT_PIPX_GLOBAL_MAN_DIR: Final[Path] = Path("/usr/local/share/man")

# Overrides for testing
OVERRIDE_PIPX_HOME = None
OVERRIDE_PIPX_BIN_DIR = None
OVERRIDE_PIPX_MAN_DIR = None
OVERRIDE_PIPX_SHARED_LIBS = None
OVERRIDE_PIPX_GLOBAL_HOME = None
OVERRIDE_PIPX_GLOBAL_BIN_DIR = None
OVERRIDE_PIPX_GLOBAL_MAN_DIR = None

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def get_expanded_environ(env_name: str) -> Path | None:
    return Path(value).expanduser().absolute() if (value := get_environment_value(env_name)) else None


class _PathContext:
    _base_home: Path | None
    _default_home: Path
    _base_bin: Path | None
    _default_bin: Path
    _base_man: Path | None
    _default_man: Path
    _default_log: Path
    _default_cache: Path
    _default_trash: Path
    _base_shared_libs: Path | None
    _fallback_home: Path | None
    _home_exists: bool
    log_file: Path | None = None

    def __init__(self) -> None:
        self.make_local()

    @property
    def venvs(self) -> Path:
        return self.home / "venvs"

    @property
    def logs(self) -> Path:
        if self._home_exists or not LINUX:
            return self.home / "logs"
        return self._default_log

    @property
    def trash(self) -> Path:
        if self._home_exists:
            return self.home / ".trash"
        return self._default_trash

    @property
    def venv_cache(self) -> Path:
        if self._home_exists or not LINUX:
            return self.home / ".cache"
        return self._default_cache

    @cached_property
    def bin_dir(self) -> Path:
        return (self._base_bin or self._default_bin).resolve()

    @cached_property
    def man_dir(self) -> Path:
        return (self._base_man or self._default_man).resolve()

    @cached_property
    def home(self) -> Path:
        if self._base_home:
            home = self._base_home
        elif self._fallback_home:
            home = self._fallback_home
        else:
            home = self._default_home
        return home.absolute()

    @cached_property
    def shared_libs(self) -> Path:
        return (self._base_shared_libs or self.home / "shared").resolve()

    def _clear_cached_paths(self) -> None:
        for attribute in ("bin_dir", "home", "man_dir", "shared_libs"):
            self.__dict__.pop(attribute, None)

    def make_local(self) -> None:
        self._base_home = OVERRIDE_PIPX_HOME or get_expanded_environ("PIPX_HOME")  # type: ignore[redundant-expr]
        self._default_home = DEFAULT_PIPX_HOME
        self._base_bin = OVERRIDE_PIPX_BIN_DIR or get_expanded_environ("PIPX_BIN_DIR")  # type: ignore[redundant-expr]
        self._default_bin = DEFAULT_PIPX_BIN_DIR
        self._base_man = OVERRIDE_PIPX_MAN_DIR or get_expanded_environ("PIPX_MAN_DIR")  # type: ignore[redundant-expr]
        self._default_man = DEFAULT_PIPX_MAN_DIR
        self._base_shared_libs = OVERRIDE_PIPX_SHARED_LIBS or get_expanded_environ("PIPX_SHARED_LIBS")  # type: ignore[redundant-expr]
        self._default_log = Path(user_log_path("pipx"))
        self._default_cache = Path(user_cache_path("pipx"))
        self._default_trash = self._default_home / "trash"
        self._fallback_home = next((fallback for fallback in FALLBACK_PIPX_HOMES if fallback.exists()), None)
        self._home_exists = self._base_home is not None or any(fallback.exists() for fallback in FALLBACK_PIPX_HOMES)
        self._clear_cached_paths()

    def make_global(self) -> None:
        self._base_home = OVERRIDE_PIPX_GLOBAL_HOME or get_expanded_environ("PIPX_GLOBAL_HOME")  # type: ignore[redundant-expr]
        self._default_home = DEFAULT_PIPX_GLOBAL_HOME
        self._base_bin = OVERRIDE_PIPX_GLOBAL_BIN_DIR or get_expanded_environ("PIPX_GLOBAL_BIN_DIR")  # type: ignore[redundant-expr]
        self._default_bin = DEFAULT_PIPX_GLOBAL_BIN_DIR
        self._base_man = OVERRIDE_PIPX_GLOBAL_MAN_DIR or get_expanded_environ("PIPX_GLOBAL_MAN_DIR")  # type: ignore[redundant-expr]
        self._default_man = DEFAULT_PIPX_GLOBAL_MAN_DIR
        self._default_log = self._default_home / "logs"
        self._default_cache = self._default_home / ".cache"
        self._default_trash = self._default_home / "trash"
        self._base_shared_libs = None
        self._fallback_home = None
        self._home_exists = self._base_home is not None
        self._clear_cached_paths()

    @property
    def standalone_python_cachedir(self) -> Path:
        return self.home / "py"

    @property
    def allow_spaces_in_home_path(self) -> bool:
        return strtobool(os.getenv("PIPX_HOME_ALLOW_SPACE", "0"))

    def log_warnings(self) -> None:
        if " " in str(self.home) and not self.allow_spaces_in_home_path:
            _LOGGER.warning(
                pipx_wrap(
                    (
                        f"{hazard} Found a space in the pipx home path. We heavily discourage this, due to "
                        "multiple incompatibilities. Please check our docs for more information on this, "
                        "as well as some pointers on how to migrate to a different home path."
                    ),
                    subsequent_indent=" " * 4,
                )
            )
            _LOGGER.warning(
                pipx_wrap(
                    (f"{hazard} To see your PIPX_HOME dir: pipx environment --value PIPX_HOME"),
                    subsequent_indent=" " * 4,
                )
            )
            _LOGGER.warning(
                pipx_wrap(
                    (f"{hazard} Most likely fix on macOS: mv ~/Library/Application\\ Support/pipx ~/.local/"),
                    subsequent_indent=" " * 4,
                )
            )

        fallback_home_exists = self._fallback_home is not None and self._fallback_home.exists()
        specific_home_exists = self.home != self._fallback_home
        if fallback_home_exists and specific_home_exists:
            _LOGGER.info(
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


__all__ = [
    "DEFAULT_PIPX_BIN_DIR",
    "DEFAULT_PIPX_GLOBAL_BIN_DIR",
    "DEFAULT_PIPX_GLOBAL_HOME",
    "DEFAULT_PIPX_GLOBAL_MAN_DIR",
    "DEFAULT_PIPX_HOME",
    "DEFAULT_PIPX_MAN_DIR",
    "OVERRIDE_PIPX_BIN_DIR",
    "OVERRIDE_PIPX_GLOBAL_BIN_DIR",
    "OVERRIDE_PIPX_GLOBAL_HOME",
    "OVERRIDE_PIPX_GLOBAL_MAN_DIR",
    "OVERRIDE_PIPX_HOME",
    "OVERRIDE_PIPX_MAN_DIR",
    "OVERRIDE_PIPX_SHARED_LIBS",
    "ctx",
    "get_expanded_environ",
]
