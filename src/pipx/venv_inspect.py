import json
import logging
import textwrap
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata  # type: ignore

from pipx.constants import WINDOWS
from pipx.util import PipxError, run_subprocess

logger = logging.getLogger(__name__)


class VenvInspectInformation(NamedTuple):
    distributions: List[metadata.Distribution]
    env: Dict[str, str]
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
    dist: metadata.Distribution, extras: Set[str], env: Dict[str, str]
) -> List[Requirement]:
    eval_env = env.copy()
    # Add an empty extra to enable evaluation of non-extra markers
    if not extras:
        extras.add("")
    dependencies = []
    for req in map(Requirement, dist.requires or []):
        if not req.marker:
            dependencies.append(req)
        else:
            for extra in extras:
                eval_env["extra"] = extra
                if req.marker.evaluate(eval_env):
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
        # vast speedup by ignoring all paths not above distribution root dir
        #   (venv/bin or venv/Scripts is above distribution root)
        if Path(path).parts[0] != "..":
            continue

        dist_file_path = Path(dist.locate_file(path))
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
    dist: metadata.Distribution,
    package_req: Requirement,
    venv_inspect_info: VenvInspectInformation,
    app_paths_of_dependencies: Dict[str, List[Path]],
    dep_visited: Optional[Dict[str, bool]] = None,
) -> Dict[str, List[Path]]:
    if dep_visited is None:
        # Initialize: we have already visited root
        dep_visited = {canonicalize_name(package_req.name): True}

    dependencies = get_package_dependencies(
        dist, package_req.extras, venv_inspect_info.env
    )
    for dep_req in dependencies:
        dep_name = canonicalize_name(dep_req.name)
        if dep_name in dep_visited:
            # avoid infinite recursion, avoid duplicates in info
            continue

        dep_dist = get_dist(dep_req.name, venv_inspect_info.distributions)
        if dep_dist is None:
            raise PipxError(
                "Pipx Internal Error: cannot find package {dep_req.name!r} metadata."
            )
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


def fetch_info_in_venv(venv_python_path: Path) -> Tuple[List[str], Dict[str, str], str]:
    command_str = textwrap.dedent(
        """
        import json
        import os
        import platform
        import sys

        impl_ver = sys.implementation.version
        implementation_version = "{0.major}.{0.minor}.{0.micro}".format(impl_ver)
        if impl_ver.releaselevel != "final":
            implementation_version = "{}{}{}".format(
                implementation_version,
                impl_ver.releaselevel[0],
                impl_ver.serial,
            )

        sys_path = sys.path
        try:
            sys_path.remove("")
        except ValueError:
            pass

        print(
            json.dumps(
                {
                    "sys_path": sys_path,
                    "python_version": "{0.major}.{0.minor}.{0.micro}".format(sys.version_info),
                    "environment": {
                        "implementation_name": sys.implementation.name,
                        "implementation_version": implementation_version,
                        "os_name": os.name,
                        "platform_machine": platform.machine(),
                        "platform_release": platform.release(),
                        "platform_system": platform.system(),
                        "platform_version": platform.version(),
                        "python_full_version": platform.python_version(),
                        "platform_python_implementation": platform.python_implementation(),
                        "python_version": ".".join(platform.python_version_tuple()[:2]),
                        "sys_platform": sys.platform,
                    },
                }
            )
        )
        """
    )
    venv_info = json.loads(
        run_subprocess(
            [venv_python_path, "-c", command_str],
            capture_stderr=False,
            log_cmd_str="<fetch_info_in_venv commands>",
        ).stdout
    )
    return (
        venv_info["sys_path"],
        venv_info["environment"],
        f"Python {venv_info['python_version']}",
    )


def inspect_venv(
    root_package_name: str,
    root_package_extras: Set[str],
    venv_bin_path: Path,
    venv_python_path: Path,
) -> VenvMetadata:
    app_paths_of_dependencies: Dict[str, List[Path]] = {}
    apps_of_dependencies: List[str] = []

    root_req = Requirement(root_package_name)
    root_req.extras = root_package_extras

    (venv_sys_path, venv_env, venv_python_version) = fetch_info_in_venv(
        venv_python_path
    )

    venv_inspect_info = VenvInspectInformation(
        bin_path=venv_bin_path,
        env=venv_env,
        distributions=list(metadata.distributions(path=venv_sys_path)),
    )

    root_dist = get_dist(root_req.name, venv_inspect_info.distributions)
    if root_dist is None:
        raise PipxError(
            "Pipx Internal Error: cannot find package {root_req.name!r} metadata."
        )
    app_paths_of_dependencies = _dfs_package_apps(
        root_dist, root_req, venv_inspect_info, app_paths_of_dependencies
    )

    apps = get_apps(root_dist, venv_bin_path)
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
        package_version=root_dist.version,
        python_version=venv_python_version,
    )

    return venv_metadata
