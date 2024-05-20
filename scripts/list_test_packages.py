#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Set

from test_packages_support import get_platform_list_path


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
        description="Create list of needed test packages for pipx tests and local pypiserver."
    )

    # specifying nargs= puts outputs of parser in list (even if nargs=1)

    # required arguments
    parser.add_argument(
        "primary_package_list",
        help="Main packages to examine, getting list of matching distribution files and dependencies.",
    )
    parser.add_argument("package_list_dir", help="Directory to output package distribution lists.")

    # switches/options:
    parser.add_argument("-v", "--verbose", action="store_true", help="Maximum verbosity, especially for pip operations.")

    return parser.parse_args(argv)


def parse_package_list(package_list_file: Path) -> List[Dict[str, Any]]:
    output_list: List[Dict[str, Any]] = []
    try:
        with package_list_file.open("r") as package_list_fh:
            for line in package_list_fh:
                line_parsed = re.sub(r"#.+$", "", line)
                if not re.search(r"\S", line_parsed):
                    continue
                line_list = line_parsed.strip().split()
                if len(line_list) == 1:
                    output_list.append({"spec": line_list[0]})
                elif len(line_list) == 2:
                    output_list.append({"spec": line_list[0], "no-deps": line_list[1].lower() == "true"})
                else:
                    print(f"ERROR: Unable to parse primary package list line:\n    {line.strip()}")
                    return []
    except OSError:
        print("ERROR: File problem reading primary package list.")
        return []
    return output_list


def create_test_packages_list(package_list_dir_path: Path, primary_package_list_path: Path, verbose: bool) -> int:
    exit_code = 0
    package_list_dir_path.mkdir(exist_ok=True)
    platform_package_list_path = get_platform_list_path(package_list_dir_path)

    primary_test_packages = parse_package_list(primary_package_list_path)
    if not primary_test_packages:
        print(f"ERROR: Problem reading {primary_package_list_path}.  Exiting.", file=sys.stderr)
        return 1

    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(download, pkg, verbose) for pkg in primary_test_packages}
        downloaded_list = set()
        for future in as_completed(futures):
            downloaded_list.update(future.result())

    all_packages = []
    for downloaded_path in downloaded_list:
        wheel_re = re.search(r"([^-]+)-([^-]+)-([^-]+)\-([^-]+)-([^-]+)(-[^-]+)?\.whl$", downloaded_path)
        src_re = re.search(r"(.+)-([^-]+)\.(?:tar.gz|zip)$", downloaded_path)
        if wheel_re:
            package_name = wheel_re.group(1)
            package_version = wheel_re.group(2)
        elif src_re:
            package_name = src_re.group(1)
            package_version = src_re.group(2)
        else:
            print(f"ERROR: cannot parse: {downloaded_path}", file=sys.stderr)
            continue

        all_packages.append(f"{package_name}=={package_version}")

    with platform_package_list_path.open("w") as package_list_fh:
        for package in sorted(all_packages):
            print(package, file=package_list_fh)

    return exit_code


def download(test_package: Dict[str, str], verbose: bool) -> Set[str]:
    no_deps = test_package.get("no-deps", False)
    test_package_option_string = " (no-deps)" if no_deps else ""
    verbose_this_iteration = False
    with tempfile.TemporaryDirectory() as download_dir:
        cmd_list = ["pip", "download"] + (["--no-deps"] if no_deps else []) + [test_package["spec"], "-d", download_dir]
        if verbose:
            print(f"CMD: {' '.join(cmd_list)}")
        pip_download_process = subprocess.run(cmd_list, capture_output=True, text=True, check=False)
        if pip_download_process.returncode == 0:
            print(f"Examined {test_package['spec']}{test_package_option_string}")
        else:
            print(f"ERROR with {test_package['spec']}{test_package_option_string}", file=sys.stderr)
            verbose_this_iteration = True
        if verbose or verbose_this_iteration:
            print(pip_download_process.stdout)
            print(pip_download_process.stderr)
        return {i.name for i in Path(download_dir).iterdir()}


def main(argv: List[str]) -> int:
    args = process_command_line(argv)

    return create_test_packages_list(Path(args.package_list_dir), Path(args.primary_package_list), args.verbose)


if __name__ == "__main__":
    try:
        status = main(sys.argv)
    except KeyboardInterrupt:
        print("Stopped by Keyboard Interrupt", file=sys.stderr)
        status = 130

    sys.exit(status)
