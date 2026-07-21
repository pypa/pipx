from __future__ import annotations

import platform
import sys
import sysconfig
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Free-threaded builds need cp3XXt wheels, so they resolve and seed a cache of their own instead of sharing the
# same-version GIL build's directory; the "t" suffix also matches the "3.XXt" naming CI keys its cache on.
PYTHON_VERSION_STR = (
    f"{sys.version_info[0]}.{sys.version_info[1]}{'t' if sysconfig.get_config_var('Py_GIL_DISABLED') else ''}"
)

# Platform logic
if sys.platform == "darwin":
    FULL_PLATFORM = "macos" + platform.release().split(".")[0]
elif sys.platform == "win32":
    FULL_PLATFORM = "win"
else:
    FULL_PLATFORM = "unix"


def get_platform_list_path(package_list_dir_path: Path) -> Path:
    return package_list_dir_path / f"{FULL_PLATFORM}-python{PYTHON_VERSION_STR}.txt"


def get_platform_packages_dir_path(pipx_package_cache_path: Path) -> Path:
    return pipx_package_cache_path / f"{PYTHON_VERSION_STR}"
