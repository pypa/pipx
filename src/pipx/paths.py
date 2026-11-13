from __future__ import annotations

__lazy_modules__ = ["pipx.self_install", "pipx.wrap", "typing"]

import logging
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Final

from platformdirs import user_cache_path, user_data_path, user_log_path

from pipx.constants import WINDOWS
from pipx.self_install import DEFAULT_PIPX_GLOBAL_HOME, get_environment_value
from pipx.wrap import pipx_wrap

#: Default directory of the pipx home, in the user data directory.
DEFAULT_PIPX_HOME: Final[Path] = user_data_path("pipx")
FALLBACK_PIPX_HOMES: Final[list[Path]] = [Path.home() / ".local/pipx", *([Path.home() / "pipx"] if WINDOWS else [])]

#: Default directory of the user's binaries that pipx exposes apps in.
DEFAULT_PIPX_BIN_DIR: Final[Path] = Path.home() / ".local/bin"
#: Default directory of the user's man pages that pipx exposes man pages in.
DEFAULT_PIPX_MAN_DIR: Final[Path] = Path.home() / ".local/share/man"
#: Default directory of the global binaries that pipx exposes apps in, for global installs.
DEFAULT_PIPX_GLOBAL_BIN_DIR: Final[Path] = Path("/usr/local/bin")
#: Default directory of the global man pages that pipx exposes man pages in, for global installs.
DEFAULT_PIPX_GLOBAL_MAN_DIR: Final[Path] = Path("/usr/local/share/man")

# tests point these at temporary directories so no test touches the real pipx locations
#: Directory that replaces the pipx home, set by the code that embeds pipx; None to use the environment.
OVERRIDE_PIPX_HOME: Path | None = None
#: Directory that replaces the directory of the user's binaries, set by the code that embeds pipx.
OVERRIDE_PIPX_BIN_DIR: Path | None = None
#: Directory that replaces the directory of the user's man pages, set by the code that embeds pipx.
OVERRIDE_PIPX_MAN_DIR: Path | None = None
#: Directory that replaces the directory of the completion scripts, set by the code that embeds pipx.
OVERRIDE_PIPX_COMPLETION_DIR: Path | None = None
#: Directory that replaces the shared libraries directory, set by the code that embeds pipx.
OVERRIDE_PIPX_SHARED_LIBS: Path | None = None
#: Directory that replaces the global pipx home, set by the code that embeds pipx.
OVERRIDE_PIPX_GLOBAL_HOME: Path | None = None
#: Directory that replaces the global binaries directory, set by the code that embeds pipx.
OVERRIDE_PIPX_GLOBAL_BIN_DIR: Path | None = None
#: Directory that replaces the global man pages directory, set by the code that embeds pipx.
OVERRIDE_PIPX_GLOBAL_MAN_DIR: Path | None = None
#: Directory that replaces the global completion scripts directory, set by the code that embeds pipx.
OVERRIDE_PIPX_GLOBAL_COMPLETION_DIR: Path | None = None
#: Directory that replaces the global shared libraries directory, set by the code that embeds pipx.
OVERRIDE_PIPX_GLOBAL_SHARED_LIBS: Path | None = None

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


# a directory the environment or the embedding code chose; None falls back to the default
@dataclass(frozen=True, slots=True, kw_only=True)
class _ChosenDirs:
    home: Path | None
    bin_dir: Path | None
    man_dir: Path | None
    completion_dir: Path | None
    shared_libs: Path | None


@dataclass(frozen=True, slots=True, kw_only=True)
class _DefaultDirs:
    home: Path
    bin_dir: Path
    man_dir: Path
    completion_dir: Path
    log: Path
    cache: Path
    trash: Path


class _PathContext:
    _chosen: _ChosenDirs
    _default: _DefaultDirs
    _fallback_home: Path | None
    _home_exists: bool
    log_file: Path | None = None

    def __init__(self) -> None:
        self.make_local()

    def make_local(self) -> None:
        self._chosen = _ChosenDirs(
            home=OVERRIDE_PIPX_HOME or get_expanded_environ("PIPX_HOME"),
            bin_dir=OVERRIDE_PIPX_BIN_DIR or get_expanded_environ("PIPX_BIN_DIR"),
            man_dir=OVERRIDE_PIPX_MAN_DIR or get_expanded_environ("PIPX_MAN_DIR"),
            completion_dir=OVERRIDE_PIPX_COMPLETION_DIR or get_expanded_environ("PIPX_COMPLETION_DIR"),
            shared_libs=OVERRIDE_PIPX_SHARED_LIBS or get_expanded_environ("PIPX_SHARED_LIBS"),
        )
        self._default = _DefaultDirs(
            home=DEFAULT_PIPX_HOME,
            bin_dir=DEFAULT_PIPX_BIN_DIR,
            man_dir=DEFAULT_PIPX_MAN_DIR,
            completion_dir=Path.home() / ".local/share",
            log=user_log_path("pipx"),
            cache=user_cache_path("pipx"),
            trash=DEFAULT_PIPX_HOME / "trash",
        )
        self._fallback_home = next((fallback for fallback in FALLBACK_PIPX_HOMES if fallback.exists()), None)
        self._home_exists = self._chosen.home is not None or any(fallback.exists() for fallback in FALLBACK_PIPX_HOMES)
        self._clear_cached_paths()

    def _clear_cached_paths(self) -> None:
        for attribute in ("bin_dir", "completion_dir", "home", "man_dir", "shared_libs"):
            self.__dict__.pop(attribute, None)

    @property
    def venvs(self) -> Path:
        return self.home / "venvs"

    @cached_property
    def home(self) -> Path:
        return (self._chosen.home or self._fallback_home or self._default.home).absolute()

    @property
    def logs(self) -> Path:
        # a legacy home keeps holding the venvs, yet its logs and cache belong in the platform locations, so only an
        # explicit PIPX_HOME pulls them back under the home
        return self.home / "logs" if self._chosen.home else self._default.log

    @property
    def venv_cache(self) -> Path:
        return self.home / ".cache" if self._chosen.home else self._default.cache

    @property
    def trash(self) -> Path:
        # renaming into the trash has to stay on one filesystem, so it follows the venvs under the home
        return self.home / ".trash" if self._home_exists else self._default.trash

    @cached_property
    def bin_dir(self) -> Path:
        return (self._chosen.bin_dir or self._default.bin_dir).resolve()

    @cached_property
    def man_dir(self) -> Path:
        return (self._chosen.man_dir or self._default.man_dir).resolve()

    @cached_property
    def completion_dir(self) -> Path:
        return (self._chosen.completion_dir or self._default.completion_dir).resolve()

    @cached_property
    def shared_libs(self) -> Path:
        return (self._chosen.shared_libs or self.home / "shared").resolve()

    @property
    def standalone_python_cachedir(self) -> Path:
        return self.home / "py"

    def make_global(self) -> None:
        self._chosen = _ChosenDirs(
            home=OVERRIDE_PIPX_GLOBAL_HOME or get_expanded_environ("PIPX_GLOBAL_HOME"),
            bin_dir=OVERRIDE_PIPX_GLOBAL_BIN_DIR or get_expanded_environ("PIPX_GLOBAL_BIN_DIR"),
            man_dir=OVERRIDE_PIPX_GLOBAL_MAN_DIR or get_expanded_environ("PIPX_GLOBAL_MAN_DIR"),
            completion_dir=OVERRIDE_PIPX_GLOBAL_COMPLETION_DIR or get_expanded_environ("PIPX_GLOBAL_COMPLETION_DIR"),
            shared_libs=OVERRIDE_PIPX_GLOBAL_SHARED_LIBS,
        )
        self._default = _DefaultDirs(
            home=DEFAULT_PIPX_GLOBAL_HOME,
            bin_dir=DEFAULT_PIPX_GLOBAL_BIN_DIR,
            man_dir=DEFAULT_PIPX_GLOBAL_MAN_DIR,
            completion_dir=Path("/usr/local/share"),
            log=DEFAULT_PIPX_GLOBAL_HOME / "logs",
            cache=DEFAULT_PIPX_GLOBAL_HOME / ".cache",
            trash=DEFAULT_PIPX_GLOBAL_HOME / "trash",
        )
        self._fallback_home = None
        self._home_exists = self._chosen.home is not None
        self._clear_cached_paths()

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
    """Return the path that an environment variable names, expanded and made absolute.

    :param env_name: the environment variable to read, such as ``PIPX_HOME``.
    :returns: the path, or None when the variable is not set.
    """
    return Path(value).expanduser().absolute() if (value := get_environment_value(env_name)) else None


#: The paths that pipx uses, resolved from the environment and the overrides.
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
