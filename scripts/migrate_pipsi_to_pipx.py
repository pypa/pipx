#!/usr/bin/env python3

"""Migrate the packages pipsi manages to pipx."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from shutil import which
from typing import Final


def main() -> None:
    if not which("pipx"):
        sys.exit("pipx must be installed to migrate from pipsi to pipx")

    if not sys.stdout.isatty():
        sys.exit("Must be run from a terminal, not a script")

    pipsi_home: Final = os.environ.get("PIPSI_HOME", Path("~/.local/venvs/").expanduser())
    if not (packages := [path.name for path in Path(pipsi_home).iterdir()]):
        sys.exit(0)

    while (answer := input("Continue? [y/n] ")) not in {"y", "n"}:
        pass
    if answer == "n":
        sys.exit(0)

    for package in packages:
        if not subprocess.run(["pipsi", "uninstall", "--yes", package], check=False).returncode:  # ruff:ignore[start-process-with-partial-path]  # pipsi resolved from PATH
            subprocess.run(["pipx", "install", package], check=False)  # ruff:ignore[start-process-with-partial-path]  # pipx resolved from PATH


if __name__ == "__main__":
    main()
