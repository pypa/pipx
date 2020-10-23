import json
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Optional

try:
    from importlib import metadata  # type: ignore
except ImportError:
    import importlib_metadata as metadata  # type: ignore

from packaging.requirements import Requirement

try:
    WindowsError
except NameError:
    WINDOWS = False
else:
    WINDOWS = True

# TODO: make sure to test with package with extras


def get_package_dependencies(package: str) -> List[Requirement]:
    extras = Requirement(package).extras

    return [
        str(req)
        for req in map(Requirement, metadata.requires(package) or [])  # type: ignore
        if not req.marker or req.marker.evaluate({"extra": extras})
    ]


def get_package_version(package: str) -> Optional[str]:
    return metadata.version(package)  # type: ignore


def get_apps(package: str, bin_path: Path) -> List[str]:
    import pkg_resources

    dist = pkg_resources.get_distribution(package)

    apps = set()
    for section in ["console_scripts", "gui_scripts"]:
        # "entry_points" entry in setup.py are found here
        for name in pkg_resources.get_entry_map(dist).get(section, []):
            if (bin_path / name).exists():
                apps.add(name)
            if WINDOWS and (bin_path / (name + ".exe")).exists():
                # WINDOWS adds .exe to entry_point name
                apps.add(name + ".exe")

    if dist.has_metadata("RECORD"):
        # for non-editable package installs, RECORD is list of installed files
        # "scripts" entry in setup.py is found here (test w/ awscli)
        for line in dist.get_metadata_lines("RECORD"):
            entry = line.split(",")[0]  # noqa: T484
            path = (Path(dist.location) / entry).resolve()
            try:
                if path.parent.samefile(bin_path):
                    apps.add(Path(entry).name)
            except FileNotFoundError:
                pass

    if dist.has_metadata("installed-files.txt"):
        # not sure what is found here
        for line in dist.get_metadata_lines("installed-files.txt"):
            entry = line.split(",")[0]  # noqa: T484
            path = (Path(dist.egg_info) / entry).resolve()  # type: ignore
            try:
                if path.parent.samefile(bin_path):
                    apps.add(Path(entry).name)
            except FileNotFoundError:
                pass

    return sorted(apps)


def _dfs_package_apps(
    bin_path: Path,
    package: str,
    app_paths_of_dependencies: Dict[str, List[Path]],
    dep_visited: Optional[Dict[str, bool]] = None,
) -> Dict[str, List[Path]]:
    if dep_visited is None:
        dep_visited = {}

    dependencies = get_package_dependencies(package)
    for req in dependencies:
        app_names = get_apps(req.name, bin_path)
        if app_names:
            app_paths_of_dependencies[req.name] = [bin_path / app for app in app_names]
        # recursively search for more
        if req.name not in dep_visited:
            # only search if this package isn't already listed to avoid
            # infinite recursion
            dep_visited[req.name] = True
            app_paths_of_dependencies = _dfs_package_apps(
                bin_path, req.name, app_paths_of_dependencies, dep_visited
            )
    return app_paths_of_dependencies


def _windows_extra_app_paths(app_paths: List[Path]) -> List[Path]:
    # In Windows, editable package have additional files starting with the
    #   same name that are required to be in the same dir to run the app
    # Add "*-script.py", "*.exe.manifest" only to app_paths to make
    #   execution work; do not add them to apps to ensure they are not listed
    app_paths_output = app_paths.copy()
    for app_path in app_paths:
        win_app_path = app_path.parent / (app_path.stem + "-script.py")
        if win_app_path.exists():
            app_paths_output.append(win_app_path)
        win_app_path = app_path.parent / (app_path.stem + ".exe.manifest")
        if win_app_path.exists():
            app_paths_output.append(win_app_path)
    return app_paths_output


def main():
    package = sys.argv[1]
    bin_path = Path(sys.argv[2])

    apps = get_apps(package, bin_path)
    app_paths = [Path(bin_path) / app for app in apps]
    if WINDOWS:
        app_paths = _windows_extra_app_paths(app_paths)
    app_paths = [str(app_path) for app_path in app_paths]

    app_paths_of_dependencies = {}  # type: Dict[str, List[str]]
    apps_of_dependencies = []  # type: List[str]
    app_paths_of_dependencies = _dfs_package_apps(
        bin_path, package, app_paths_of_dependencies
    )
    for dep in app_paths_of_dependencies:
        apps_of_dependencies += [
            dep_path.name for dep_path in app_paths_of_dependencies[dep]
        ]
        if WINDOWS:
            app_paths_of_dependencies[dep] = _windows_extra_app_paths(
                app_paths_of_dependencies[dep]
            )
        app_paths_of_dependencies[dep] = [
            str(dep_path) for dep_path in app_paths_of_dependencies[dep]
        ]

    output = {
        "apps": apps,
        "app_paths": app_paths,
        "apps_of_dependencies": apps_of_dependencies,
        "app_paths_of_dependencies": app_paths_of_dependencies,
        "package_version": get_package_version(package),
        "python_version": "Python {}.{}.{}".format(
            sys.version_info.major, sys.version_info.minor, sys.version_info.micro
        ),
    }

    print(json.dumps(output))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(
            json.dumps(
                {
                    "apps": [],
                    "app_paths": [],
                    "apps_of_dependencies": [],
                    "app_paths_of_dependencies": {},
                    "package_version": None,
                    "python_version": None,
                    "exception_traceback": traceback.format_exc().rstrip(),
                }
            )
        )
