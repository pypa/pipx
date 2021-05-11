#!/usr/bin/env python3
"""Usage:
    python3 scripts/list_test_packages.py > test_package_list.txt
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List

PRIMARY_TEST_PACKAGES = [
    "setuptools>=41.0",
    "ansible==2.9.13",
    "awscli==1.18.168",
    "black==18.9.b0",
    "black==20.8b1",
    "cloudtoken==0.1.707",
    "ipython==7.16.1",
    "isort==5.6.4",
    "jaraco-clipboard==2.0.1",
    "jaraco-financial==2.0.0",
    "jupyter==1.0.0",
    "kaggle==1.5.9",
    "nox==2020.8.22",
    "pbr==5.6.0",
    "pip",
    "pycowsay==0.0.0.1",
    "pygdbmi==0.10.0.0",
    "pylint",
    "pylint==2.3.1",
    "setuptools-scm",
    "shell-functools==0.3.0",
    "tox",
    "tox-ini-fmt==0.5.0",
    "weblate==4.3.1",
    "wheel",
]

# Platform logic
if sys.platform == "darwin":
    PLATFORM = "macos"
elif sys.platform == "win32":
    PLATFORM = "win"
else:
    PLATFORM = "unix"


def main(argv: List[str]) -> int:
    exit_code = 0
    if len(argv) < 2:
        print(
            "Please supply the directory to output the package distribution list as first argument.",
            file=sys.stderr,
        )
    package_list_dir_path = Path(argv[1])
    package_list_dir_path.mkdir(exist_ok=True)
    package_list_path = (
        package_list_dir_path
        / f"{PLATFORM}-{sys.version_info[0]}.{sys.version_info[1]}.txt"
    )

    with tempfile.TemporaryDirectory() as download_dir:
        for primary_test_package in PRIMARY_TEST_PACKAGES:
            pip_download_process = subprocess.run(
                ["pip", "download", primary_test_package, "-d", str(download_dir)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            if pip_download_process.returncode == 0:
                print(f"Examined {primary_test_package}")
            else:
                # Assume if pip download fails, then this package is meant to
                #   fail in the tests.  Try just downloading the main package
                #   without its dependencies.  This will allow pipx to get
                #   somewhere in installing it and print a better error.
                # pip download needs to run setup.py to determine deps for
                #   packages that use setup.py.  Thus it can fail simply in the
                #   process of downloading packages.
                pip_download_process2 = subprocess.run(
                    [
                        "pip",
                        "download",
                        "--no-deps",
                        primary_test_package,
                        "-d",
                        str(download_dir),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                )
                if pip_download_process2.returncode == 0:
                    print(
                        f"WARNING: {primary_test_package} was downloaded "
                        "but NOT its deps.",
                        file=sys.stderr,
                    )
                else:
                    print(f"ERROR with {primary_test_package}", file=sys.stderr)
                    print(pip_download_process.stdout, file=sys.stderr)
                    print(pip_download_process.stderr, file=sys.stderr)
                    exit_code = 1
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
