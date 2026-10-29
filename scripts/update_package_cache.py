#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Final

from list_test_packages import create_test_packages_list
from test_packages_support import get_platform_list_path, get_platform_packages_dir_path


class _Options(argparse.Namespace):
    package_list_dir: Path
    pipx_package_cache_dir: Path
    check_only: bool


def main(argv: list[str]) -> int:
    parser: Final = argparse.ArgumentParser(
        description="Check and update as needed the pipx tests package cache "
        "for use with the pipx tests local pypiserver."
    )
    parser.add_argument(
        "package_list_dir",
        type=Path,
        help="Directory where platform- and python-specific package lists are found for pipx tests.",
    )
    parser.add_argument(
        "pipx_package_cache_dir",
        type=Path,
        help="Directory to store the packages distribution files.",
    )
    parser.add_argument(
        "-c",
        "--check-only",
        action="store_true",
        help="Only check to see if needed packages are in PACKAGES_DIR, do not download or delete files.",
    )
    options: Final = parser.parse_args(argv[1:], namespace=_Options())
    return _update_test_packages_cache(
        options.package_list_dir, options.pipx_package_cache_dir, check_only=options.check_only
    )


def _update_test_packages_cache(package_list_dir_path: Path, pipx_package_cache_path: Path, *, check_only: bool) -> int:
    packages_dir_path: Final[Path] = get_platform_packages_dir_path(pipx_package_cache_path)
    packages_dir_path.mkdir(exist_ok=True, parents=True)
    packages_dir_files: Final[list[Path]] = list(packages_dir_path.iterdir())

    platform_package_list_path: Final[Path] = get_platform_list_path(package_list_dir_path)
    if not platform_package_list_path.exists() and create_test_packages_list(
        package_list_dir_path, package_list_dir_path / "primary_packages.txt"
    ):
        return 1
    try:
        platform_package_list_fh = platform_package_list_path.open()
    except OSError:
        return 1

    exit_code = 0
    packages_dir_missing: Final[list[str]] = []
    with platform_package_list_fh:
        for line in platform_package_list_fh:
            if not (package_spec_match := re.search(r"^(.+)==(.+)$", package_spec := line.strip())):
                exit_code = 1
                continue
            package_name, package_version = package_spec_match.groups()
            package_dist_pattern = rf"{re.escape(package_name)}-{re.escape(package_version)}(.tar.gz|.zip|-)"
            if matches := [path for path in packages_dir_files if re.search(package_dist_pattern, path.name)]:
                for matched_file in matches:
                    packages_dir_files.remove(matched_file)
            else:
                packages_dir_missing.append(package_spec)

    if check_only:
        return 1 if packages_dir_missing else 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_download, package_spec, packages_dir_path) for package_spec in packages_dir_missing}
        for future in as_completed(futures):
            exit_code = future.result() or exit_code

    for unused_file in packages_dir_files:
        unused_file.unlink()

    return exit_code


def _download(package_spec: str, packages_dir_path: Path) -> int:
    pip_download: Final = subprocess.run(
        [sys.executable, "-m", "pip", "download", "--no-deps", package_spec, "-d", str(packages_dir_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return 0 if pip_download.returncode == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        sys.exit(130)
