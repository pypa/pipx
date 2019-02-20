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
            path = (Path(dist.egg_info) / entry).resolve()  # type: ignore
            try:
                if path.parent.samefile(bin_path):
                    binaries.add(Path(entry).name)
            except FileNotFoundError:
                pass

    return sorted(binaries)


def main():
    package = sys.argv[1]
    bin_path = Path(sys.argv[2])

    binaries = get_binaries(package, bin_path)
    binary_paths = [str(Path(bin_path) / binary) for binary in binaries]
    dependencies = get_package_dependencies(package)
    binaries_of_dependencies: Dict[str, List[str]] = {}
    for dep in dependencies:
        dep_binaries = get_binaries(dep, bin_path)
        if dep_binaries:
            binaries_of_dependencies[dep] = dep_binaries

    print(
        json.dumps(
            {
                "binaries": binaries,
                "binary_paths": binary_paths,
                "dependencies": dependencies,
                "binaries_of_dependencies": binaries_of_dependencies,
                "package_version": get_package_version(package),
                "python_version": f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(
            json.dumps(
                {
                    "binaries": [],
                    "binary_paths": [],
                    "dependencies": [],
                    "binaries_of_dependencies": {},
                    "package_version": None,
                    "python_version": None,
                }
            )
        )
