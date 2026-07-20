from __future__ import annotations

import ast
import configparser
import json
import logging
import shutil
import sys
import textwrap
from importlib import metadata
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Final, NamedTuple
from urllib.parse import urlparse
from urllib.request import url2pathname

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from pipx.constants import COMPLETION_SECTIONS, MAN_SECTIONS, WINDOWS
from pipx.util import PipxError, run_subprocess

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping

logger = logging.getLogger(__name__)

_DATA_FILE_PAIR_LEN: Final[int] = 2
_MIN_MAN_TARGET_PARTS: Final[int] = 2


class VenvInspectInformation(NamedTuple):
    distributions: Mapping[str, metadata.Distribution]
    env: dict[str, str]
    bin_path: Path
    man_path: Path


class VenvMetadata(NamedTuple):
    apps: list[str]
    app_paths: list[Path]
    apps_of_dependencies: list[str]
    app_paths_of_dependencies: dict[str, list[Path]]
    man_pages: list[str]
    man_paths: list[Path]
    man_pages_of_dependencies: list[str]
    man_paths_of_dependencies: dict[str, list[Path]]
    completions: list[str]
    completion_paths: list[Path]
    completions_of_dependencies: list[str]
    completion_paths_of_dependencies: dict[str, list[Path]]
    package_version: str
    python_version: str


def get_distributions_by_name(paths: list[str]) -> dict[str, metadata.Distribution]:
    metadata.MetadataPathFinder().invalidate_caches()
    return {canonicalize_name(name): dist for dist in metadata.distributions(path=paths) if (name := dist.name)}


def get_package_dependencies(dist: metadata.Distribution, extras: set[str], env: dict[str, str]) -> list[Requirement]:
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


def get_required_dependency_names(dist: metadata.Distribution, env: dict[str, str]) -> set[str]:
    """Canonical names ``dist`` depends on, including dependencies behind its declared extras.

    Considering every declared extra is deliberately conservative: a dependency that is only pulled
    in by an extra is still treated as required, so it is never reported as removable while the
    package declaring it stays installed.
    """
    extras = set(dist.metadata.get_all("Provides-Extra") or [])
    return {canonicalize_name(req.name) for req in get_package_dependencies(dist, extras, env)}


def list_not_required_packages(venv_python: Path) -> set[str]:
    """Canonical names of installed packages that no other installed package requires.

    Mirrors ``pip list --not-required`` from installed distribution metadata so every backend
    (including uv, which lacks the flag) computes the same result.
    """
    venv_sys_path, venv_env, _ = fetch_info_in_venv(venv_python)
    distributions = tuple(metadata.distributions(path=venv_sys_path))
    installed: set[str] = set()
    required: set[str] = set()
    for dist in distributions:
        if (name := dist.metadata["Name"]) is not None:
            installed.add(canonicalize_name(name))
        required |= get_required_dependency_names(dist, venv_env)
    return installed - required


def get_apps_from_entry_points(dist: metadata.Distribution, bin_path: Path) -> set[str]:
    app_names = set()
    sections = {"console_scripts", "gui_scripts"}
    # "entry_points" entry in setup.py are found here
    for ep in dist.entry_points:
        if ep.group not in sections:
            continue
        if (bin_path / ep.name).exists():
            app_names.add(ep.name)
        if WINDOWS and (bin_path / (ep.name + ".exe")).exists():
            # WINDOWS adds .exe to entry_point name
            app_names.add(ep.name + ".exe")
    return app_names


def get_resources_from_dist_files(
    dist: metadata.Distribution, bin_path: Path, man_path: Path
) -> tuple[set[str], set[str], set[str]]:
    app_names = set()
    man_names = set()
    completion_names = set()
    # search installed files
    # "scripts" entry in setup.py is found here (test w/ awscli)
    for path in dist.files or []:
        # vast speedup by ignoring all paths not above distribution root dir
        #   (venv/bin or venv/Scripts is above distribution root)
        if Path(path).parts[0] != "..":
            continue

        dist_file_path = Path(str(dist.locate_file(path)))
        try:
            if dist_file_path.parent.samefile(bin_path):
                app_names.add(path.name)
            if dist_file_path.parent.name in MAN_SECTIONS and dist_file_path.parent.parent.samefile(man_path):
                man_names.add(str(Path(dist_file_path.parent.name) / path.name))
        except FileNotFoundError:
            pass
        if completion_name := _get_completion_name(dist_file_path, man_path.parent):
            completion_names.add(completion_name)
    return app_names, man_names, completion_names


def get_resources_from_inst_files(
    dist: metadata.Distribution, bin_path: Path, man_path: Path
) -> tuple[set[str], set[str], set[str]]:
    app_names = set()
    man_names = set()
    completion_names = set()
    # not sure what is found here
    inst_files = dist.read_text("installed-files.txt") or ""
    for line in inst_files.splitlines():
        entry = line.split(",")[0]
        inst_file_path = Path(str(dist.locate_file(entry))).resolve()
        try:
            if inst_file_path.parent.samefile(bin_path):
                app_names.add(inst_file_path.name)
            if inst_file_path.parent.name in MAN_SECTIONS and inst_file_path.parent.parent.samefile(man_path):
                man_names.add(str(Path(inst_file_path.parent.name) / inst_file_path.name))
        except FileNotFoundError:
            pass
        if completion_name := _get_completion_name(inst_file_path, man_path.parent):
            completion_names.add(completion_name)
    return app_names, man_names, completion_names


def _same_file(left: Path, right: Path) -> bool:
    try:
        return left.samefile(right)
    except OSError:
        return False


def _get_completion_name(file_path: Path, share_path: Path) -> str | None:
    # a wheel ships its completion scripts in the data scheme, which lands them beside the man pages under share/
    for section in COMPLETION_SECTIONS:
        if _same_file(file_path.parent, share_path / section):
            return str(section / file_path.name)
    return None


def get_resources(
    dist: metadata.Distribution, bin_path: Path, man_path: Path
) -> tuple[list[str], list[str], list[str]]:
    app_names_ep = get_apps_from_entry_points(dist, bin_path)
    app_names_df, man_names_df, completion_names_df = get_resources_from_dist_files(dist, bin_path, man_path)
    app_names_if, man_names_if, completion_names_if = get_resources_from_inst_files(dist, bin_path, man_path)
    app_names = app_names_ep | app_names_df | app_names_if
    man_names = man_names_df | man_names_if | _get_man_pages_from_editable_project(dist, man_path)
    completion_names = completion_names_df | completion_names_if
    return sorted(app_names), sorted(man_names), sorted(completion_names)


def _get_man_pages_from_editable_project(dist: metadata.Distribution, man_path: Path) -> set[str]:
    project_root = _get_editable_project_root(dist)
    if project_root is None:
        return set()

    man_names = set()
    for target_dir, source_paths in _iter_editable_project_data_files(project_root):
        man_section = _get_man_section_from_data_files_target(target_dir)
        if man_section is None:
            continue
        for source_path in source_paths:
            source = Path(source_path)
            if not source.is_absolute():
                source = project_root / source
            if not source.is_file():
                continue
            dest = man_path / man_section / source.name
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
            except OSError as exc:
                logger.warning("Unable to copy editable man page %s to %s: %s", source, dest, exc)
                continue
            man_names.add(str(Path(man_section) / source.name))

    return man_names


def _get_editable_project_root(dist: metadata.Distribution) -> Path | None:
    direct_url = dist.read_text("direct_url.json")
    if not direct_url:
        return None
    try:
        data = json.loads(direct_url)
    except json.JSONDecodeError:
        return None

    dir_info = data.get("dir_info", {})
    if not isinstance(dir_info, dict) or not dir_info.get("editable"):
        return None

    url = data.get("url")
    if not isinstance(url, str):
        return None
    parsed_url = urlparse(url)
    if parsed_url.scheme != "file":
        return None

    url_path = f"//{parsed_url.netloc}{parsed_url.path}" if parsed_url.netloc else parsed_url.path
    return Path(url2pathname(url_path))


def _iter_editable_project_data_files(project_root: Path) -> Iterator[tuple[str, list[str]]]:
    yield from _iter_pyproject_data_files(project_root)
    yield from _iter_setup_cfg_data_files(project_root)
    yield from _iter_setup_py_data_files(project_root)


def _iter_pyproject_data_files(project_root: Path) -> Iterator[tuple[str, list[str]]]:
    pyproject = project_root / "pyproject.toml"
    try:
        with pyproject.open("rb") as file:
            pyproject_data = tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError):
        return

    data_files = pyproject_data.get("tool", {}).get("setuptools", {}).get("data-files", {})
    yield from _iter_normalized_data_files(data_files)


def _iter_setup_cfg_data_files(project_root: Path) -> Iterator[tuple[str, list[str]]]:
    setup_cfg = project_root / "setup.cfg"
    config = configparser.ConfigParser(interpolation=None)
    try:
        config.read(setup_cfg)
    except configparser.Error:
        return
    if not config.has_section("options.data_files"):
        return

    yield from _iter_normalized_data_files(dict(config.items("options.data_files")))


def _iter_setup_py_data_files(project_root: Path) -> Iterator[tuple[str, list[str]]]:
    setup_py = project_root / "setup.py"
    try:
        tree = ast.parse(setup_py.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_setup_call(node):
            continue
        for keyword in node.keywords:
            if keyword.arg != "data_files":
                continue
            try:
                data_files = ast.literal_eval(keyword.value)
            except (ValueError, SyntaxError):
                return
            yield from _iter_normalized_data_files(data_files)
            return


def _is_setup_call(node: ast.Call) -> bool:
    return (isinstance(node.func, ast.Name) and node.func.id == "setup") or (
        isinstance(node.func, ast.Attribute) and node.func.attr == "setup"
    )


def _iter_normalized_data_files(data_files: object) -> Iterator[tuple[str, list[str]]]:
    items: Iterable[object]
    if isinstance(data_files, dict):
        items = data_files.items()
    elif isinstance(data_files, (list, tuple)):
        items = data_files
    else:
        return

    for item in items:
        if not isinstance(item, (list, tuple)) or len(item) != _DATA_FILE_PAIR_LEN:
            continue
        target_dir, source_paths = item
        if not isinstance(target_dir, str):
            continue
        if isinstance(source_paths, str):
            yield target_dir, [line.strip() for line in source_paths.splitlines() if line.strip()]
        elif isinstance(source_paths, (list, tuple)) and all(isinstance(path, str) for path in source_paths):
            yield target_dir, [path for path in source_paths if isinstance(path, str)]


def _get_man_section_from_data_files_target(target_dir: str) -> str | None:
    parts = PurePosixPath(target_dir.replace("\\", "/")).parts
    if len(parts) < _MIN_MAN_TARGET_PARTS or parts[-2] != "man" or parts[-1] not in MAN_SECTIONS:
        return None
    return parts[-1]


def _dfs_package_resources(  # ruff:ignore[too-many-arguments]  # threads three resource accumulators plus the visited set through recursion
    dist: metadata.Distribution,
    package_req: Requirement,
    venv_inspect_info: VenvInspectInformation,
    *,
    app_paths_of_dependencies: dict[str, list[Path]],
    man_paths_of_dependencies: dict[str, list[Path]],
    completion_paths_of_dependencies: dict[str, list[Path]],
    dep_visited: dict[str, bool] | None = None,
) -> tuple[dict[str, list[Path]], dict[str, list[Path]], dict[str, list[Path]]]:
    if dep_visited is None:
        # Initialize: we have already visited root
        dep_visited = {canonicalize_name(package_req.name): True}

    share_path: Final[Path] = venv_inspect_info.man_path.parent
    dependencies = get_package_dependencies(dist, package_req.extras, venv_inspect_info.env)
    for dep_req in dependencies:
        dep_name = canonicalize_name(dep_req.name)
        if dep_name in dep_visited:
            # avoid infinite recursion, avoid duplicates in info
            continue

        dep_dist = venv_inspect_info.distributions.get(dep_name)
        if dep_dist is None:
            msg = f"Pipx Internal Error: cannot find package {dep_req.name!r} metadata."
            raise PipxError(msg)
        app_names, man_names, completion_names = get_resources(
            dep_dist, venv_inspect_info.bin_path, venv_inspect_info.man_path
        )
        if app_names:
            app_paths_of_dependencies[dep_name] = [venv_inspect_info.bin_path / name for name in app_names]
        if man_names:
            man_paths_of_dependencies[dep_name] = [venv_inspect_info.man_path / name for name in man_names]
        if completion_names:
            completion_paths_of_dependencies[dep_name] = [share_path / name for name in completion_names]
        # recursively search for more
        dep_visited[dep_name] = True
        app_paths_of_dependencies, man_paths_of_dependencies, completion_paths_of_dependencies = _dfs_package_resources(
            dep_dist,
            dep_req,
            venv_inspect_info,
            app_paths_of_dependencies=app_paths_of_dependencies,
            man_paths_of_dependencies=man_paths_of_dependencies,
            completion_paths_of_dependencies=completion_paths_of_dependencies,
            dep_visited=dep_visited,
        )
    return app_paths_of_dependencies, man_paths_of_dependencies, completion_paths_of_dependencies


def _windows_extra_app_paths(app_paths: list[Path]) -> list[Path]:
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


def fetch_info_in_venv(venv_python_path: Path) -> tuple[list[str], dict[str, str], str]:
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


def inspect_venv(  # ruff:ignore[too-many-locals]  # aggregates apps, man pages, and completions for root and deps into one VenvMetadata
    root_package_name: str,
    root_package_extras: set[str],
    venv_bin_path: Path,
    venv_python_path: Path,
    venv_man_path: Path,
) -> VenvMetadata:
    app_paths_of_dependencies: dict[str, list[Path]] = {}
    apps_of_dependencies: list[str] = []
    man_paths_of_dependencies: dict[str, list[Path]] = {}
    man_pages_of_dependencies: list[str] = []
    completion_paths_of_dependencies: dict[str, list[Path]] = {}
    completions_of_dependencies: list[str] = []

    root_req = Requirement(root_package_name)
    root_req.extras = root_package_extras

    (venv_sys_path, venv_env, venv_python_version) = fetch_info_in_venv(venv_python_path)

    distributions = get_distributions_by_name(venv_sys_path)

    venv_inspect_info = VenvInspectInformation(
        bin_path=venv_bin_path,
        man_path=venv_man_path,
        env=venv_env,
        distributions=distributions,
    )

    root_dist = venv_inspect_info.distributions.get(canonicalize_name(root_req.name))
    if root_dist is None:
        msg = f"Pipx Internal Error: cannot find package {root_req.name!r} metadata."
        raise PipxError(msg)
    app_paths_of_dependencies, man_paths_of_dependencies, completion_paths_of_dependencies = _dfs_package_resources(
        root_dist,
        root_req,
        venv_inspect_info,
        app_paths_of_dependencies=app_paths_of_dependencies,
        man_paths_of_dependencies=man_paths_of_dependencies,
        completion_paths_of_dependencies=completion_paths_of_dependencies,
    )

    venv_share_path: Final[Path] = venv_man_path.parent
    apps, man_pages, completions = get_resources(root_dist, venv_bin_path, venv_man_path)
    app_paths = [venv_bin_path / app for app in apps]
    man_paths = [venv_man_path / man_page for man_page in man_pages]
    completion_paths = [venv_share_path / completion for completion in completions]
    if WINDOWS:
        app_paths = _windows_extra_app_paths(app_paths)

    for dep in app_paths_of_dependencies:
        apps_of_dependencies += [dep_path.name for dep_path in app_paths_of_dependencies[dep]]
        if WINDOWS:
            app_paths_of_dependencies[dep] = _windows_extra_app_paths(app_paths_of_dependencies[dep])
    for dep in man_paths_of_dependencies:
        man_pages_of_dependencies += [
            str(Path(dep_path.parent.name) / dep_path.name) for dep_path in man_paths_of_dependencies[dep]
        ]
    for dep in completion_paths_of_dependencies:
        completions_of_dependencies += [
            dep_path.relative_to(venv_share_path).as_posix() for dep_path in completion_paths_of_dependencies[dep]
        ]

    return VenvMetadata(
        apps=apps,
        app_paths=app_paths,
        apps_of_dependencies=apps_of_dependencies,
        app_paths_of_dependencies=app_paths_of_dependencies,
        man_pages=man_pages,
        man_paths=man_paths,
        man_pages_of_dependencies=man_pages_of_dependencies,
        man_paths_of_dependencies=man_paths_of_dependencies,
        completions=completions,
        completion_paths=completion_paths,
        completions_of_dependencies=completions_of_dependencies,
        completion_paths_of_dependencies=completion_paths_of_dependencies,
        package_version=root_dist.version,
        python_version=venv_python_version,
    )


__all__ = [
    "VenvMetadata",
    "fetch_info_in_venv",
    "get_distributions_by_name",
    "get_required_dependency_names",
    "inspect_venv",
    "list_not_required_packages",
]
