#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from test_packages_support import get_platform_list_path


class _Options(argparse.Namespace):
    primary_package_list: Path
    package_list_dir: Path
    verbose: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class _TestPackage:
    spec: str
    no_deps: bool


def main(argv: list[str]) -> int:
    parser: Final = argparse.ArgumentParser(
        description="Create list of needed test packages for pipx tests and local pypiserver."
    )
    parser.add_argument(
        "primary_package_list",
        type=Path,
        help="Main packages to examine, getting list of matching distribution files and dependencies.",
    )
    parser.add_argument("package_list_dir", type=Path, help="Directory to output package distribution lists.")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Maximum verbosity, especially for pip operations."
    )
    options: Final = parser.parse_args(argv[1:], namespace=_Options())
    return create_test_packages_list(options.package_list_dir, options.primary_package_list)


def create_test_packages_list(package_list_dir_path: Path, primary_package_list_path: Path) -> int:
    package_list_dir_path.mkdir(exist_ok=True)
    if not (primary_test_packages := _parse_package_list(primary_package_list_path)):
        return 1

    exit_code = 0
    downloaded: Final[set[str]] = set()
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(_download, package) for package in primary_test_packages}
        for future in as_completed(futures):
            try:
                downloaded.update(future.result())
            except subprocess.CalledProcessError as error:
                sys.stderr.write(f"{shlex.join(error.cmd)} failed:\n{error.stderr}")
                exit_code = 1
    # a partial list would stick around and fail tests with "no matching distribution", so write none
    if exit_code:
        return exit_code

    package_specs: Final[list[str]] = sorted(
        f"{match.group(1)}=={match.group(2)}"
        for downloaded_path in downloaded
        if (
            match := re.search(r"([^-]+)-([^-]+)-([^-]+)\-([^-]+)-([^-]+)(-[^-]+)?\.whl$", downloaded_path)
            or re.search(r"(.+)-([^-]+)\.(?:tar.gz|zip)$", downloaded_path)
        )
    )
    with get_platform_list_path(package_list_dir_path).open("w") as package_list_fh:
        package_list_fh.writelines(f"{package_spec}\n" for package_spec in package_specs)
    return exit_code


def _parse_package_list(package_list_file: Path) -> list[_TestPackage]:
    try:
        with package_list_file.open("r", encoding="utf-8") as package_list_fh:
            lines: Final[list[str]] = list(package_list_fh)
    except OSError:
        return []
    test_packages: Final[list[_TestPackage]] = []
    for line in lines:
        match re.sub(r"#.+$", "", line).split():
            case []:
                continue
            case [spec]:
                test_packages.append(_TestPackage(spec=spec, no_deps=False))
            case [spec, no_deps]:
                test_packages.append(_TestPackage(spec=spec, no_deps=no_deps.lower() == "true"))
            case _:
                return []
    return test_packages


def _download(test_package: _TestPackage) -> set[str]:
    with tempfile.TemporaryDirectory() as download_dir:
        subprocess.run(
            [  # ruff:ignore[start-process-with-partial-path]  # whichever pip is on PATH
                "pip",
                "download",
                *(["--no-deps"] if test_package.no_deps else []),
                test_package.spec,
                "-d",
                download_dir,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return {path.name for path in Path(download_dir).iterdir()}


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        sys.exit(130)


__all__ = [
    "create_test_packages_list",
]
