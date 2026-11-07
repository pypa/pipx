from __future__ import annotations

__lazy_modules__ = ["pathlib", "pipx.redact", "pipx.wrap"]

import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

from pipx.constants import MINGW, WINDOWS
from pipx.redact import redact_url_credentials
from pipx.wrap import pipx_wrap

if TYPE_CHECKING:
    from collections.abc import Sequence

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


class PipxError(Exception):
    def __init__(self, message: str, *, wrap_message: bool = True, backend_output: str = "") -> None:
        self.raw_message: Final[str] = message
        # what pip or uv said, for a result envelope to carry when the terminal already showed it live
        self.backend_output: Final[str] = backend_output
        super().__init__(pipx_wrap(message) if wrap_message else message)


class InstalledNameMismatchError(PipxError):
    def __init__(self, installed_name: str) -> None:
        self.installed_name: Final[str] = installed_name
        super().__init__(f"The package spec installed {installed_name!r}, a different name than expected.")


def mkdir(path: Path) -> None:
    if path.is_dir():
        return
    _LOGGER.info("creating directory %s", path)
    path.mkdir(parents=True, exist_ok=True)


def get_pypackage_bin_path(binary_name: str) -> Path:
    return Path("__pypackages__") / f"{sys.version_info.major}.{sys.version_info.minor}" / "lib" / "bin" / binary_name


if WINDOWS:

    def get_venv_paths(root: Path) -> tuple[Path, Path, Path]:
        # the Microsoft Store Python redirects paths for sandboxing, so work from the real root:
        # https://github.com/pypa/pipx/issues/1164
        real_root: Final[Path] = root.resolve()
        bin_path: Final[Path] = real_root / ("bin" if MINGW else "Scripts")
        return bin_path, bin_path / "python.exe", real_root / "share" / "man"

else:

    def get_venv_paths(root: Path) -> tuple[Path, Path, Path]:
        bin_path: Final[Path] = root / "bin"
        return bin_path, bin_path / "python", root / "share" / "man"


def open_owner_only(path: str | os.PathLike[str], flags: int) -> int:
    # logs record command lines that can carry secrets, and a global store keeps them under a world-readable /opt/pipx
    return os.open(path, flags, 0o600)


def full_package_description(package_name: str, package_spec: str) -> str:
    if package_name == package_spec:
        return redact_url_credentials(package_name)
    return f"{package_name} from spec {redact_url_credentials(package_spec)!r}"


def is_file_name(name: str) -> bool:
    # joined to a directory, ".." names its parent and a separator or a drive leads anywhere
    return name not in {"", ".."} and Path(name).name == name


def reject_empty_index(pip_args: Sequence[str]) -> None:
    # an empty value usually comes from an unset variable, as in --index-url "$INDEX_URL", and uv reads it as the
    # default index
    for position, argument in enumerate(pip_args):
        option, separator, value = argument.partition("=")
        if option not in {"--default-index", "--extra-index-url", "--index", "--index-url", "-i"} or (
            not separator and position + 1 == len(pip_args)
        ):
            continue
        if not (value if separator else pip_args[position + 1]).strip():
            msg = f"{option} is empty; pass the index URL or leave the option out"
            raise PipxError(msg)


__all__ = [
    "InstalledNameMismatchError",
    "PipxError",
    "full_package_description",
    "get_pypackage_bin_path",
    "get_venv_paths",
    "is_file_name",
    "mkdir",
    "open_owner_only",
    "reject_empty_index",
]
