from __future__ import annotations

import platform
import sys
import sysconfig
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path

# free-threaded builds need cp3XXt wheels, so they resolve and seed a cache of their own instead of sharing the
# same-version GIL build's directory; the "t" suffix also matches the "3.XXt" naming CI keys its cache on
_PYTHON_VERSION_STR: Final[str] = (
    f"{sys.version_info[0]}.{sys.version_info[1]}{'t' if sysconfig.get_config_var('Py_GIL_DISABLED') else ''}"
)


def get_platform_list_path(package_list_dir_path: Path) -> Path:
    match sys.platform:
        case "darwin":
            full_platform = f"macos{platform.release().split('.')[0]}"
        case "win32":
            full_platform = "win"
        case _:
            full_platform = "unix"
    return package_list_dir_path / f"{full_platform}-python{_PYTHON_VERSION_STR}.txt"


def get_platform_packages_dir_path(pipx_package_cache_path: Path) -> Path:
    return pipx_package_cache_path / _PYTHON_VERSION_STR


__all__ = [
    "get_platform_list_path",
    "get_platform_packages_dir_path",
]
