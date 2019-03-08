#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from pathlib import Path
import sys
import json
from typing import Dict, List, Optional


def get_package_dependencies(package: str) -> List[str]:
    try:
        import pkg_resources
    except Exception:
        return []
    return [str(r) for r in pkg_resources.get_distribution(package).requires()]


def get_package_version(package: str) -> Optional[str]:
    try:
        import pkg_resources

        return pkg_resources.get_distribution(package).version
    except Exception:
        return None


def get_binaries(package: str, bin_path: Path) -> List[str]:
    try:
        import pkg_resources
    except Exception:
        return []
    dist = pkg_resources.get_distribution(package)

    binaries = set()
    for section in ["console_scripts", "gui_scripts"]:
        # "entry_points" entry in setup.py are found here
        for name in pkg_resources.get_entry_map(dist).get(section, []):
            binaries.add(name)

    if dist.has_metadata("RECORD"):
        # "scripts" entry in setup.py is found here (test w/ awscli)
        for line in dist.get_metadata_lines("RECORD"):
            entry = line.split(",")[0]  # noqa: T484
            path = (Path(dist.location) / entry).resolve()
            try:
                if path.parent.samefile(bin_path):
                    binaries.add(Path(entry).name)
            except FileNotFoundError:
                pass

    if dist.has_metadata("installed-files.txt"):
        # not sure what is found here
        for line in dist.get_metadata_lines("installed-files.txt"):
            entry = line.split(",")[0]  # noqa: T484
            path = (Path(dist.egg_info) / entry).resolve()  # type: ignore
            try:
                if path.parent.samefile(bin_path):
                    binaries.add(Path(entry).name)
            except FileNotFoundError:
                pass

    return sorted(binaries)


def _dfs_package_binaries(
    bin_path: Path, package: str, binary_paths_of_dependencies: Dict[str, List[str]]
):
    dependencies = get_package_dependencies(package)
    for d in dependencies:
        binary_names = get_binaries(d, bin_path)
        if binary_names:
            binaries = [str(Path(bin_path) / binary) for binary in binary_names]
            binary_paths_of_dependencies[d] = binaries
        # recursively search for more
        if d not in binary_paths_of_dependencies:
            # only search if this package isn't already listed to avoid
            # infinite recursion
            binary_paths_of_dependencies = _dfs_package_binaries(
                bin_path, d, binary_paths_of_dependencies
            )
    return binary_paths_of_dependencies


def main():
    package = sys.argv[1]
    bin_path = Path(sys.argv[2])

    binaries = get_binaries(package, bin_path)
    binary_paths = [str(Path(bin_path) / binary) for binary in binaries]
    binary_paths_of_dependencies: Dict[str, List[str]] = {}
    binary_paths_of_dependencies = _dfs_package_binaries(
        bin_path, package, binary_paths_of_dependencies
    )

    output = {
        "binaries": binaries,
        "binary_paths": binary_paths,
        "binary_paths_of_dependencies": binary_paths_of_dependencies,
        "package_version": get_package_version(package),
        "python_version": f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }

    print(json.dumps(output))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(
            json.dumps(
                {
                    "binaries": [],
                    "binary_paths": [],
                    "binary_paths_of_dependencies": {},
                    "package_version": None,
                    "python_version": None,
                }
            )
        )
