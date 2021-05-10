#!/usr/bin/env python3
"""Usage:
    python3 scripts/list_test_packages.py > test_package_list.txt
"""
import os
import re
import subprocess
import sys
import tempfile
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
    "pylint==2.5.3",
    "setuptools-scm",
    "shell-functools==0.3.0",
    "tox",
    "tox-ini-fmt==0.5.0",
    "weblate==4.3.1",
    "wheel",
]


def main(argv: List[str]) -> int:
    with tempfile.TemporaryDirectory() as download_dir:
        for primary_test_package in PRIMARY_TEST_PACKAGES:
            pip_download_process = subprocess.run(
                ["pip", "download", primary_test_package, "-d", str(download_dir)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            print(pip_download_process.stdout, file=sys.stderr)
            print(pip_download_process.stderr, file=sys.stderr)
        downloaded_list = os.listdir(download_dir)

    for downloaded_filename in downloaded_list:
        wheel_re = re.search(
            r"(.+)\-([^-]+)\-([^-]+)\-([^-]+)\-([^-]+)\.whl$", downloaded_filename
        )
        src_re = re.search(r"(.+)\-([^-]+)\.tar.gz$", downloaded_filename)
        if wheel_re:
            package_name = wheel_re.group(1)
            package_version = wheel_re.group(2)
        elif src_re:
            package_name = src_re.group(1)
            package_version = src_re.group(2)
        else:
            print(f"ERROR: cannot parse: {downloaded_filename}", file=sys.stderr)
            continue

        print(f"{package_name}=={package_version}")
    return 0


if __name__ == "__main__":
    try:
        status = main(sys.argv)
    except KeyboardInterrupt:
        print("Stopped by Keyboard Interrupt", file=sys.stderr)
        status = 130

    sys.exit(status)
