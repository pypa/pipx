#!/usr/bin/env python3

"""
Script to migrate from pipsi to pipx
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from shutil import which


def main() -> None:
    if not which("pipx"):
        sys.exit("pipx must be installed to migrate from pipsi to pipx")

    if not sys.stdout.isatty():
        sys.exit("Must be run from a terminal, not a script")

    pipsi_home = os.environ.get("PIPSI_HOME", Path("~/.local/venvs/").expanduser())
    packages = [p.name for p in Path(pipsi_home).iterdir()]

    if not packages:
        sys.exit(0)

    for _package in packages:
        pass

    answer = None
    while answer not in {"y", "n"}:
        answer = input("Continue? [y/n] ")

    if answer == "n":
        sys.exit(0)

    for package in packages:
        ret = subprocess.run(["pipsi", "uninstall", "--yes", package], check=False)  # ruff:ignore[start-process-with-partial-path]  # pipsi resolved from PATH
        if ret.returncode:
            pass
        else:
            ret = subprocess.run(["pipx", "install", package], check=False)  # ruff:ignore[start-process-with-partial-path]  # pipx resolved from PATH


if __name__ == "__main__":
    main()
