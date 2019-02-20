#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pkg_resources
from pathlib import Path
import sys


def get_binaries(package: str, bin_path: Path):
    dist = pkg_resources.get_distribution(package)

    binaries = set()
    for section in ["console_scripts", "gui_scripts"]:
        for name in pkg_resources.get_entry_map(dist).get(section, []):
            binaries.add(name)

    if dist.has_metadata("RECORD"):
        for line in dist.get_metadata_lines("RECORD"):
            entry = line.split(",")[0]
            path = (Path(dist.location) / entry).resolve()
            try:
                if path.parent.name == "scripts" in entry or path.parent.samefile(
                    bin_path
                ):
                    binaries.add(Path(entry).name)
            except FileNotFoundError:
                pass

    if dist.has_metadata("installed-files.txt"):
        for line in dist.get_metadata_lines("installed-files.txt"):
            entry = line.split(",")[0]
            path = (Path(dist.egg_info) / entry).resolve()
            try:
                if path.parent.samefile(bin_path):
                    binaries.add(Path(entry).name)
            except FileNotFoundError:
                pass

    return sorted(binaries)


if __name__ == "__main__":
    package = sys.argv[1]
    bin_path = Path(sys.argv[2])
    binaries = get_binaries(package, bin_path)
    for b in binaries:
        print(b)
