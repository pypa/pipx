import platform
import sys
from pathlib import Path

# Platform logic
if sys.platform == "darwin":
    PLATFORM = "macos"
    FULL_PLATFORM = "macos" + platform.release().split(".")[0]
elif sys.platform == "win32":
    PLATFORM = "win"
    FULL_PLATFORM = "win"
else:
    PLATFORM = "unix"
    FULL_PLATFORM = "unix"


def get_platform_list_path(package_list_dir_path: Path) -> Path:
    platform_package_list_path = (
        package_list_dir_path
        / f"{FULL_PLATFORM}-python{sys.version_info[0]}.{sys.version_info[1]}.txt"
    )
    return platform_package_list_path


def get_platform_packages_dir_path(pipx_package_cache_path: Path) -> Path:
    platform_packages_dir_path = (
        pipx_package_cache_path / f"{sys.version_info[0]}.{sys.version_info[1]}"
    )
    return platform_packages_dir_path
