#!/usr/bin/env python3
"""Usage:
    python3 scripts/list_test_packages.py > test_package_list.txt
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

# Modify this list if the packages pipx installs in tests change
PRIMARY_TEST_PACKAGES: List[Dict[str, Any]] = [
    {"spec": "setuptools>=41.0"},
    {"spec": "ansible==2.9.13"},
    {"spec": "awscli==1.18.168"},
    {"spec": "black==18.9.b0"},
    {"spec": "black==20.8b1"},
    {"spec": "cloudtoken==0.1.707"},
    {"spec": "ipython==7.16.1"},
    {"spec": "isort==5.6.4"},
    {"spec": "jaraco-clipboard==2.0.1"},
    {"spec": "jaraco-financial==2.0.0"},
    {"spec": "jupyter==1.0.0"},
    {"spec": "kaggle==1.5.9"},
    {"spec": "nox==2020.8.22"},
    {"spec": "pbr==5.6.0"},
    {"spec": "pip"},
    {"spec": "pycowsay==0.0.0.1"},
    {"spec": "pygdbmi==0.10.0.0"},
    {"spec": "pylint"},
    {"spec": "pylint==2.3.1"},
    {"spec": "setuptools-scm"},
    {"spec": "shell-functools==0.3.0"},
    {"spec": "tox"},
    {"spec": "tox-ini-fmt==0.5.0"},
    {"spec": "weblate==4.3.1", "no-deps": True},  # expected fail in tests
    {"spec": "wheel"},
]

# Platform logic
if sys.platform == "darwin":
    PLATFORM = "macos"
elif sys.platform == "win32":
    PLATFORM = "win"
else:
    PLATFORM = "unix"


def process_command_line(argv):
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
        "package_list_dir", help="Directory to output package distribution lists."
    )

    # switches/options:
    # parser.add_argument(
    #    '-s', '--max_size', action='store',
    #    help='String specifying maximum size of images.  ' \
    #            'Larger images will be resized. (e.g. "1024x768")')
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Maximum verbosity, especially for pip operations.",
    )

    args = parser.parse_args(argv)

    return args


def main(argv: List[str]) -> int:
    exit_code = 0
    args = process_command_line(argv)
    package_list_dir_path = Path(args.package_list_dir)
    package_list_dir_path.mkdir(exist_ok=True)
    package_list_path = (
        package_list_dir_path
        / f"{PLATFORM}-{sys.version_info[0]}.{sys.version_info[1]}.txt"
    )

    with tempfile.TemporaryDirectory() as download_dir:
        for test_package in PRIMARY_TEST_PACKAGES:
            test_package_option_string = (
                " (no-deps)" if test_package.get("no-deps", False) else ""
            )
            verbose_this_iteration = False
            cmd_list = (
                ["pip", "download"]
                + (["--no-deps"] if test_package.get("no-deps", False) else [])
                + [test_package["spec"], "-d", str(download_dir)]
            )
            if args.verbose:
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
            if args.verbose or verbose_this_iteration:
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

    with package_list_path.open("w") as package_list_fh:
        for package in sorted(all_packages):
            print(package, file=package_list_fh)

    return exit_code


if __name__ == "__main__":
    try:
        status = main(sys.argv)
    except KeyboardInterrupt:
        print("Stopped by Keyboard Interrupt", file=sys.stderr)
        status = 130

    sys.exit(status)
