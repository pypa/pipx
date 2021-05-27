#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

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
        help="Main packages to examine, getting list of "
        "matching distribution files and dependencies.",
    )
    parser.add_argument(
        "package_list_dir", help="Directory to output package distribution lists."
    )

    # switches/options:
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Maximum verbosity, especially for pip operations.",
    )

    args = parser.parse_args(argv)

    return args


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
                    output_list.append(
                        {
                            "spec": line_list[0],
                            "no-deps": line_list[1].lower() == "true",
                        }
                    )
                else:
                    print(
                        f"ERROR: Unable to parse primary package list line:\n    {line.strip()}"
                    )
                    return []
    except IOError:
        print("ERROR: File problem reading primary package list.")
        return []
    return output_list


def create_test_packages_list(
    package_list_dir_path: Path, primary_package_list_path: Path, verbose: bool
) -> int:
    exit_code = 0
    package_list_dir_path.mkdir(exist_ok=True)
    platform_package_list_path = get_platform_list_path(package_list_dir_path)

    primary_test_packages = parse_package_list(primary_package_list_path)
    if not primary_test_packages:
        print(
            f"ERROR: Problem reading {primary_package_list_path}.  Exiting.",
            file=sys.stderr,
        )
        return 1

    with tempfile.TemporaryDirectory() as download_dir:
        for test_package in primary_test_packages:
            test_package_option_string = (
                " (no-deps)" if test_package.get("no-deps", False) else ""
            )
            verbose_this_iteration = False
            cmd_list = (
                ["pip", "download"]
                + (["--no-deps"] if test_package.get("no-deps", False) else [])
                + [test_package["spec"], "-d", str(download_dir)]
            )
            if verbose:
                print(f"CMD: {' '.join(cmd_list)}")
            pip_download_process = subprocess.run(
                cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            if pip_download_process.returncode == 0:
                print(f"Examined {test_package['spec']}{test_package_option_string}")
            else:
                print(
                    f"ERROR with {test_package['spec']}{test_package_option_string}",
                    file=sys.stderr,
                )
                verbose_this_iteration = True
                exit_code = 1
            if verbose or verbose_this_iteration:
                print(pip_download_process.stdout)
                print(pip_download_process.stderr)
        downloaded_list = os.listdir(download_dir)

    all_packages = []
    for downloaded_filename in downloaded_list:
        wheel_re = re.search(
            r"(.+)\-([^-]+)\-([^-]+)\-([^-]+)\-([^-]+)\.whl$", downloaded_filename
        )
        src_re = re.search(r"(.+)\-([^-]+)\.(?:tar.gz|zip)$", downloaded_filename)
        if wheel_re:
            package_name = wheel_re.group(1)
            package_version = wheel_re.group(2)
        elif src_re:
            package_name = src_re.group(1)
            package_version = src_re.group(2)
        else:
            print(f"ERROR: cannot parse: {downloaded_filename}", file=sys.stderr)
            continue

        all_packages.append(f"{package_name}=={package_version}")

    with platform_package_list_path.open("w") as package_list_fh:
        "scripts/list_test_packages.py",
        for package in sorted(all_packages):
            print(package, file=package_list_fh)

    return exit_code


def main(argv: List[str]) -> int:
    args = process_command_line(argv)

    return create_test_packages_list(
        Path(args.package_list_dir), Path(args.primary_package_list), args.verbose
    )


if __name__ == "__main__":
    try:
        status = main(sys.argv)
    except KeyboardInterrupt:
        print("Stopped by Keyboard Interrupt", file=sys.stderr)
        status = 130

    sys.exit(status)
