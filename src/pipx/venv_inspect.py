import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Set

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

try:
    from importlib import metadata  # type: ignore
except ImportError:
    import importlib_metadata as metadata  # type: ignore

from pipx.util import PipxError, run_subprocess

try:
    WindowsError
except NameError:
    WINDOWS = False
else:
    WINDOWS = True

logger = logging.getLogger(__name__)


class VenvInspectInformation(NamedTuple):
    distributions: List[metadata.Distribution]
    bin_path: Path


class VenvMetadata(NamedTuple):
    apps: List[str]
    app_paths: List[Path]
    apps_of_dependencies: List[str]
    app_paths_of_dependencies: Dict[str, List[Path]]
    package_version: str
    python_version: str


def get_dist(
    package: str, distributions: List[metadata.Distribution]
) -> Optional[metadata.Distribution]:
    """Find matching distribution in the canonicalized sense."""
    for dist in distributions:
        if canonicalize_name(dist.metadata["name"]) == canonicalize_name(package):
            return dist
    return None


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

    start_time = time.time()
    # search installed files
    # "scripts" entry in setup.py is found here (test w/ awscli)
    for path in dist.files or []:
        # vast speedup by ignoring all paths not above distribution root dir
        if Path(path).parts[0] != "..":
            continue

        dist_file_path = Path(dist.locate_file(path)).resolve()
        try:
            if dist_file_path.parent.samefile(bin_path):
                apps.add(path.name)
        except FileNotFoundError:
            pass
    logger.debug(f"installed files time: {(time.time()-start_time)*1e3:.1f}ms")

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
    dist: metadata.Distribution,
    package_req: Requirement,
    venv_inspect_info: VenvInspectInformation,
    app_paths_of_dependencies: Dict[str, List[Path]],
    dep_visited: Optional[Dict[str, bool]] = None,
) -> Dict[str, List[Path]]:
    if dep_visited is None:
        # Initialize: we have already visited root
        dep_visited = {canonicalize_name(package_req.name): True}

    dependencies = get_package_dependencies(dist, package_req.extras)
    for dep_req in dependencies:
        dep_name = canonicalize_name(dep_req.name)
        if dep_name in dep_visited:
            # avoid infinite recursion, avoid duplicates in info
            continue

        dep_dist = get_dist(dep_req.name, venv_inspect_info.distributions)
        if dep_dist is None:
            raise PipxError("Pipx Internal Error: cannot find dependent package.")
        app_names = get_apps(dep_dist, venv_inspect_info.bin_path)
        if app_names:
            app_paths_of_dependencies[dep_name] = [
                venv_inspect_info.bin_path / app for app in app_names
            ]
        # recursively search for more
        dep_visited[dep_name] = True
        app_paths_of_dependencies = _dfs_package_apps(
            dep_dist, dep_req, venv_inspect_info, app_paths_of_dependencies, dep_visited
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


def inspect_venv(
    main_req_str: str, venv_bin_path: Path, venv_python_path: Path
) -> VenvMetadata:
    main_req = Requirement(main_req_str)
    app_paths_of_dependencies: Dict[str, List[Path]] = {}
    apps_of_dependencies: List[str] = []

    start_time = time.time()
    venv_info = json.loads(
        run_subprocess(
            [
                venv_python_path,
                "-c",
                "import sys;import json;print(json.dumps({'sys_path':sys.path,'python_version':[sys.version_info.major, sys.version_info.minor, sys.version_info.micro]}))",
            ],
            capture_stderr=False,
        ).stdout
    )
    logger.debug(f"run_subprocess time: {(time.time()-start_time)*1e3:.1f}ms")

    start_time = time.time()
    venv_inspect_info = VenvInspectInformation(
        bin_path=venv_bin_path,
        distributions=list(metadata.distributions(path=venv_info["sys_path"])),
    )
    logger.debug(f"distributions time: {(time.time()-start_time)*1e3:.1f}ms")

    main_dist = get_dist(main_req.name, venv_inspect_info.distributions)
    if main_dist is None:
        raise PipxError("Pipx Internal Error: cannot find dependent package.")
    start_time = time.time()
    app_paths_of_dependencies = _dfs_package_apps(
        main_dist, main_req, venv_inspect_info, app_paths_of_dependencies
    )
    logger.debug(f"_dfs_package_apps time: {(time.time()-start_time)*1e3:.1f}ms")

    start_time = time.time()
    apps = get_apps(main_dist, venv_bin_path)
    logger.debug(f"get_apps (main) time: {(time.time()-start_time)*1e3:.1f}ms")
    app_paths = [venv_bin_path / app for app in apps]
    if WINDOWS:
        app_paths = _windows_extra_app_paths(app_paths)

    for dep in app_paths_of_dependencies:
        apps_of_dependencies += [
            dep_path.name for dep_path in app_paths_of_dependencies[dep]
        ]
        if WINDOWS:
            app_paths_of_dependencies[dep] = _windows_extra_app_paths(
                app_paths_of_dependencies[dep]
            )

    venv_metadata = VenvMetadata(
        apps=apps,
        app_paths=app_paths,
        apps_of_dependencies=apps_of_dependencies,
        app_paths_of_dependencies=app_paths_of_dependencies,
        package_version=main_dist.version,
        python_version=f"Python {venv_info['python_version'][0]}.{venv_info['python_version'][1]}.{venv_info['python_version'][2]}",
    )

    # TODO: consider removing debug message
    # logger.debug(f"venv_metadata = {venv_metadata}")

    return venv_metadata
