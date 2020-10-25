import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    from importlib import metadata  # type: ignore
except ImportError:
    import importlib_metadata as metadata  # type: ignore

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

try:
    WindowsError
except NameError:
    WINDOWS = False
else:
    WINDOWS = True


def distribution_name(package: str) -> str:
    # metadata.distribution name will not match packaging.utils.canonicalize_name()
    #   package name, e.g. if the original name has a period in it (10/24/2020)
    # Here we return the metadata.distribution matching name
    new_package: Optional[str] = None

    try:
        _ = metadata.distribution(package)
    except metadata.PackageNotFoundError:
        for test_dist in metadata.distributions():
            if canonicalize_name(test_dist.metadata["name"]) == canonicalize_name(
                package
            ):
                new_package = test_dist.metadata["name"]
                break
    else:
        new_package = package

    if new_package is None:
        raise metadata.PackageNotFoundError

    return new_package


def get_package_dependencies(
    dist: metadata.Distribution, extras: Set[Any]
) -> List[Requirement]:
    # Add an empty extra to enable evaluation of non-extra markers
    if not extras:
        extras.add("")
    dependencies = []
    for req in map(Requirement, dist.requires or []):
        if not req.marker:
            dependencies.append(req)
        else:
            for extra in extras:
                if req.marker.evaluate({"extra": extra}):
                    dependencies.append(req)
                    break

    return dependencies


def get_apps(dist: metadata.Distribution, bin_path: Path) -> List[str]:
    apps = set()

    sections = {"console_scripts", "gui_scripts"}
    # "entry_points" entry in setup.py are found here
    for ep in dist.entry_points:
        if ep.group not in sections:
            continue
        if (bin_path / ep.name).exists():
            apps.add(ep.name)
        if WINDOWS and (bin_path / (ep.name + ".exe")).exists():
            # WINDOWS adds .exe to entry_point name
            apps.add(ep.name + ".exe")

    # search installed files
    # "scripts" entry in setup.py is found here (test w/ awscli)
    for path in dist.files or []:
        dist_file_path = Path(dist.locate_file(path)).resolve()
        try:
            if dist_file_path.parent.samefile(bin_path):
                apps.add(path.name)
        except FileNotFoundError:
            pass

    # not sure what is found here
    inst_files = dist.read_text("installed-files.txt") or ""
    for line in inst_files.splitlines():
        entry = line.split(",")[0]  # noqa: T484
        inst_file_path = Path(dist.locate_file(entry)).resolve()
        try:
            if inst_file_path.parent.samefile(bin_path):
                apps.add(inst_file_path.name)
        except FileNotFoundError:
            pass

    return sorted(apps)


def _dfs_package_apps(
    bin_path: Path,
    dist: metadata.Distribution,
    package_req: Requirement,
    app_paths_of_dependencies: Dict[str, List[Path]],
    dep_visited: Optional[Dict[str, bool]] = None,
) -> Dict[str, List[Path]]:
    if dep_visited is None:
        dep_visited = {}

    dependencies = get_package_dependencies(dist, package_req.extras)
    for dep_req in dependencies:
        dep_dist = metadata.distribution(dep_req.name)

        app_names = get_apps(dep_dist, bin_path)
        if app_names:
            app_paths_of_dependencies[dep_req.name] = [
                bin_path / app for app in app_names
            ]
        # recursively search for more
        if dep_req.name not in dep_visited:
            # only search if this dep_req.name isn't already listed to avoid
            # infinite recursion
            dep_visited[dep_req.name] = True
            app_paths_of_dependencies = _dfs_package_apps(
                bin_path, dep_dist, dep_req, app_paths_of_dependencies, dep_visited
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
    package_req = Requirement(sys.argv[1])
    package_req.name = distribution_name(package_req.name)
    dist = metadata.distribution(package_req.name)
    bin_path = Path(sys.argv[2])

    apps = get_apps(dist, bin_path)
    app_paths = [Path(bin_path) / app for app in apps]
    if WINDOWS:
        app_paths = _windows_extra_app_paths(app_paths)
    app_paths = [str(app_path) for app_path in app_paths]

    app_paths_of_dependencies = {}  # type: Dict[str, List[str]]
    apps_of_dependencies = []  # type: List[str]
    app_paths_of_dependencies = _dfs_package_apps(
        bin_path, dist, package_req, app_paths_of_dependencies
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
        "package_version": dist.version,
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
