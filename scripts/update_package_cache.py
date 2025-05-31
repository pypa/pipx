#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List

from list_test_packages import create_test_packages_list
from test_packages_support import get_platform_list_path, get_platform_packages_dir_path


def process_command_line(argv: List[str]) -> argparse.Namespace:
    """Process command line invocation arguments and switches.

    Args:
        argv: list of arguments, or `None` from ``sys.argv[1:]``.

    Returns:
        argparse.Namespace: named attributes of arguments and switches
    """
    # script_name = argv[0]
    argv = argv[1:]

    # initialize the parser object:
    parser = argparse.ArgumentParser(
        description="Check and update as needed the pipx tests package cache "
        "for use with the pipx tests local pypiserver."
    )

    # specifying nargs= puts outputs of parser in list (even if nargs=1)

    # required arguments
    parser.add_argument(
        "package_list_dir",
        help="Directory where platform- and python-specific package lists are found for pipx tests.",
    )
    parser.add_argument(
        "pipx_package_cache_dir",
        help="Directory to store the packages distribution files.",
    )

    # switches/options:
    parser.add_argument(
        "-c",
        "--check-only",
        action="store_true",
        help="Only check to see if needed packages are in PACKAGES_DIR, do not download or delete files.",
    )

    return parser.parse_args(argv)


def update_test_packages_cache(package_list_dir_path: Path, pipx_package_cache_path: Path, check_only: bool) -> int:
    exit_code = 0

    platform_package_list_path = get_platform_list_path(package_list_dir_path)
    packages_dir_path = get_platform_packages_dir_path(pipx_package_cache_path)
    packages_dir_path.mkdir(exist_ok=True, parents=True)

    packages_dir_files = list(packages_dir_path.iterdir())

    if not platform_package_list_path.exists():
        print(
            f"WARNING.  File {platform_package_list_path!s}\n    does not exist.  Creating now...",
            file=sys.stderr,
        )
        create_list_returncode = create_test_packages_list(
            package_list_dir_path,
            package_list_dir_path / "primary_packages.txt",
            verbose=False,
        )
        if create_list_returncode == 0:
            print(
                f"File {platform_package_list_path!s}\n"
                "    successfully created.  Please check this file in to the"
                "    repository for future use.",
                file=sys.stderr,
            )
        else:
            print(
                f"ERROR.  Unable to create {platform_package_list_path!s}\n    Cannot continue.\n",
                file=sys.stderr,
            )
            return 1

    try:
        platform_package_list_fh = platform_package_list_path.open("r")
    except OSError:
        print(
            f"ERROR.  File {platform_package_list_path!s}\n    is not readable.  Cannot continue.\n",
            file=sys.stderr,
        )
        return 1
    else:
        platform_package_list_fh.close()

    print("Using the following file to specify needed package files:")
    print(f"    {platform_package_list_path!s}")
    print("Ensuring the following directory contains necessary package files:")
    print(f"    {packages_dir_path!s}")

    packages_dir_hits = []
    packages_dir_missing = []
    with platform_package_list_path.open("r") as platform_package_list_fh:
        for line in platform_package_list_fh:
            package_spec = line.strip()
            package_spec_re = re.search(r"^(.+)==(.+)$", package_spec)
            if not package_spec_re:
                print(f"ERROR: CANNOT PARSE {package_spec}", file=sys.stderr)
                exit_code = 1
                continue

            package_name = package_spec_re.group(1)
            package_ver = package_spec_re.group(2)
            package_dist_patt = re.escape(package_name) + r"-" + re.escape(package_ver) + r"(.tar.gz|.zip|-)"
            matches = [
                output_dir_file
                for output_dir_file in packages_dir_files
                if re.search(package_dist_patt, output_dir_file.name)
            ]
            if len(matches) == 1:
                packages_dir_files.remove(matches[0])
                packages_dir_hits.append(matches[0])
                continue
            elif len(matches) > 1:
                print(f"ERROR: more than one match for {package_spec}.", file=sys.stderr)
                print(f"    {matches}", file=sys.stderr)
                exit_code = 1
                continue

            packages_dir_missing.append(package_spec)

    print(f"MISSING FILES: {len(packages_dir_missing)}")
    print(f"EXISTING (found) FILES: {len(packages_dir_hits)}")
    print(f"LEFTOVER (unused) FILES: {len(packages_dir_files)}")

    if check_only:
        return 0 if len(packages_dir_missing) == 0 else 1
    else:
        with ThreadPoolExecutor(max_workers=12) as pool:
            futures = {pool.submit(download, pkg, packages_dir_path) for pkg in packages_dir_missing}
            for future in as_completed(futures):
                exit_code = future.result() or exit_code

        for unused_file in packages_dir_files:
            print(f"Deleting {unused_file}...")
            unused_file.unlink()

    return exit_code


def download(package_spec: str, packages_dir_path: Path) -> int:
    pip_download_process = subprocess.run(
        [
            "pip",
            "download",
            "--no-deps",
            package_spec,
            "-d",
            str(packages_dir_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if pip_download_process.returncode == 0:
        print(f"Successfully downloaded {package_spec}")
        return 0

    print(f"ERROR downloading {package_spec}", file=sys.stderr)
    print(pip_download_process.stdout, file=sys.stderr)
    print(pip_download_process.stderr, file=sys.stderr)
    return 1


def main(argv: List[str]) -> int:
    args = process_command_line(argv)
    return update_test_packages_cache(Path(args.package_list_dir), Path(args.pipx_package_cache_dir), args.check_only)


if __name__ == "__main__":
    try:
        status = main(sys.argv)
    except KeyboardInterrupt:
        print("Stopped by Keyboard Interrupt", file=sys.stderr)
        status = 130

    sys.exit(status)
