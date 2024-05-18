#!/usr/bin/env python3

"""
Script to migrate from pipsi to pipx
"""

import os
import subprocess
import sys
from pathlib import Path
from shutil import which


def main():
    if not which("pipx"):
        sys.exit("pipx must be installed to migrate from pipsi to pipx")

    if not sys.stdout.isatty():
        sys.exit("Must be run from a terminal, not a script")

    pipsi_home = os.environ.get("PIPSI_HOME", os.path.expanduser("~/.local/venvs/"))
    packages = [p.name for p in Path(pipsi_home).iterdir()]

    if not packages:
        print("No packages installed with pipsi")
        sys.exit(0)

    print("Attempting to migrate the following packages from pipsi to pipx:")
    for package in packages:
        print(f"  - {package}")

    answer = None
    while answer not in ["y", "n"]:
        answer = input("Continue? [y/n] ")

    if answer == "n":
        sys.exit(0)

    error = False
    for package in packages:
        ret = subprocess.run(["pipsi", "uninstall", "--yes", package], check=False)
        if ret.returncode:
            error = True
            print(f"Failed to uninstall {package!r} with pipsi. Not attempting to install with pipx.")
        else:
            print(f"uninstalled {package!r} with pipsi. Now attempting to install with pipx.")
            ret = subprocess.run(["pipx", "install", package], check=False)
            if ret.returncode:
                error = True
                print(f"Failed to install {package!r} with pipx.")
            else:
                print(f"Successfully installed {package} with pipx")

    print(f"Done migrating {len(packages)} packages!")
    print("You may still need to run `pipsi uninstall pipsi` or `pip uninstall pipsi`. Refer to pipsi's documentation.")

    if error:
        print("Note: Finished with errors. Review output to manually complete migration.")


if __name__ == "__main__":
    main()
