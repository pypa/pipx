import platform
import sys
from pathlib import Path

PYTHON_VERSION_STR = f"{sys.version_info[0]}.{sys.version_info[1]}"

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
