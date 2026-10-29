from __future__ import annotations

__lazy_modules__ = [
    "ast",
    "configparser",
    "importlib",
    "json",
    "packaging.requirements",
    "packaging.utils",
    "pathlib",
    "pipx.requires_python",
    "pipx.subprocess_runner",
    "pipx.util",
    "shutil",
    "textwrap",
    "tomllib",
    "urllib.parse",
]

import ast
import configparser
import json
import logging
import os
import shutil
import textwrap
import tomllib
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Final, TypedDict
from urllib.parse import urlparse

from packaging.requirements import Requirement
from packaging.utils import InvalidName, canonicalize_name

from pipx.constants import COMPLETION_SECTIONS, MAN_SECTIONS, WINDOWS
from pipx.requires_python import unsatisfied_constraint
from pipx.subprocess_runner import run_subprocess
from pipx.util import PipxError, is_file_name

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping
    from subprocess import CompletedProcess

    from packaging.specifiers import SpecifierSet

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def inspect_venv(
    root_package_name: str,
    root_package_extras: set[str],
    venv_bin_path: Path,
    venv_python_path: Path,
    venv_man_path: Path,
) -> VenvMetadata:
    root_req: Final[Requirement] = Requirement(root_package_name)
    root_req.extras = root_package_extras

    venv_sys_path, venv_env, venv_python_version = fetch_info_in_venv(venv_python_path)
    venv_inspect_info: Final[_VenvInspectInformation] = _VenvInspectInformation(
        bin_path=venv_bin_path,
        man_path=venv_man_path,
        env=venv_env,
        distributions=get_distributions_by_name(venv_sys_path),
    )

    if (root_dist := venv_inspect_info.distributions.get(canonicalize_name(root_req.name))) is None:
        msg = f"Pipx Internal Error: cannot find package {root_req.name!r} metadata."
        raise PipxError(msg)
    resources_of_dependencies: Final[_DependencyResources] = _DependencyResources(
        app_paths={}, man_paths={}, completion_paths={}
    )
    _dfs_package_resources(
        root_dist,
        root_req,
        venv_inspect_info,
        resources_of_dependencies,
        {canonicalize_name(root_req.name): set(root_package_extras)},
    )

    venv_share_path: Final[Path] = venv_man_path.parent
    apps, man_pages, completions = _get_resources(root_dist, venv_bin_path, venv_man_path)
    app_paths: Final[list[Path]] = [venv_bin_path / app for app in apps]
    # named before the Windows companion files join the paths, so those stay out of the listed apps
    apps_of_dependencies: Final[list[str]] = [
        dep_path.name for dep_paths in resources_of_dependencies.app_paths.values() for dep_path in dep_paths
    ]
    if WINDOWS:
        for dep, dep_paths in resources_of_dependencies.app_paths.items():
            resources_of_dependencies.app_paths[dep] = _windows_extra_app_paths(dep_paths)

    return VenvMetadata(
        apps=apps,
        app_paths=_windows_extra_app_paths(app_paths) if WINDOWS else app_paths,
        apps_of_dependencies=apps_of_dependencies,
        app_paths_of_dependencies=resources_of_dependencies.app_paths,
        man_pages=man_pages,
        man_paths=[venv_man_path / man_page for man_page in man_pages],
        man_pages_of_dependencies=[
            str(Path(dep_path.parent.name) / dep_path.name)
            for dep_paths in resources_of_dependencies.man_paths.values()
            for dep_path in dep_paths
        ],
        man_paths_of_dependencies=resources_of_dependencies.man_paths,
        completions=completions,
        completion_paths=[venv_share_path / completion for completion in completions],
        completions_of_dependencies=[
            dep_path.relative_to(venv_share_path).as_posix()
            for dep_paths in resources_of_dependencies.completion_paths.values()
            for dep_path in dep_paths
        ],
        completion_paths_of_dependencies=resources_of_dependencies.completion_paths,
        package_version=root_dist.version,
        python_version=f"Python {venv_env['python_full_version']}",
        unsupported_python=unsatisfied_constraint(root_dist.metadata.get("Requires-Python"), venv_python_version),
    )


def fetch_info_in_venv(venv_python_path: Path) -> tuple[list[str], dict[str, str], str]:
    command_str: Final[str] = textwrap.dedent(
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
    try:
        process: Final[CompletedProcess[str]] = run_subprocess(
            [venv_python_path, "-c", command_str],
            capture_stderr=False,
            log_cmd_str="<fetch_info_in_venv commands>",
        )
    except OSError as error:
        msg = f"Unable to run {venv_python_path}: {error}"
        raise PipxError(msg, wrap_message=False) from error
    if process.returncode:
        msg = f"{venv_python_path} exited with code {process.returncode} while pipx inspected its environment."
        raise PipxError(msg, wrap_message=False)
    try:
        venv_info: Final[_VenvInfo] = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        msg = f"{venv_python_path} printed output pipx cannot parse while inspecting its environment."
        raise PipxError(msg, wrap_message=False) from error
    return venv_info["sys_path"], venv_info["environment"], venv_info["python_version"]


class _VenvInfo(TypedDict):
    sys_path: list[str]
    environment: dict[str, str]
    python_version: str


def get_distributions_by_name(paths: list[str]) -> dict[str, metadata.Distribution]:
    metadata.MetadataPathFinder().invalidate_caches()
    distributions: Final[dict[str, metadata.Distribution]] = {}
    for dist in metadata.distributions(path=paths):
        if name := _distribution_name(dist):
            # the interpreter resolves a name to its first record on sys.path, so a later one must not shadow it
            distributions.setdefault(canonicalize_name(name), dist)
    return distributions


def _distribution_name(dist: metadata.Distribution) -> str | None:
    # uninject passes these names to the installer, which would read a metadata Name like `-t/dir` as an option
    try:
        return canonicalize_name(dist.name or "", validate=True)
    except (KeyError, InvalidName):  # Python 3.15+ raises KeyError instead of returning None when there is no Name
        return None


@dataclass(frozen=True, slots=True, kw_only=True)
class _VenvInspectInformation:
    distributions: Mapping[str, metadata.Distribution]
    env: dict[str, str]
    bin_path: Path
    man_path: Path


def _dfs_package_resources(
    dist: metadata.Distribution,
    package_req: Requirement,
    venv_inspect_info: _VenvInspectInformation,
    resources: _DependencyResources,
    dep_visited: dict[str, set[str]],
) -> None:
    share_path: Final[Path] = venv_inspect_info.man_path.parent
    for dep_req in _get_package_dependencies(dist, package_req.extras, venv_inspect_info.env):
        dep_name = canonicalize_name(dep_req.name)
        if dep_name in dep_visited and dep_req.extras <= dep_visited[dep_name]:
            # revisiting a dependency with no new extras would recurse forever and repeat its resources
            continue

        if (dep_dist := venv_inspect_info.distributions.get(dep_name)) is None:
            msg = f"Pipx Internal Error: cannot find package {dep_req.name!r} metadata."
            raise PipxError(msg)
        if dep_name not in dep_visited:
            app_names, man_names, completion_names = _get_resources(
                dep_dist, venv_inspect_info.bin_path, venv_inspect_info.man_path
            )
            if app_names:
                resources.app_paths[dep_name] = [venv_inspect_info.bin_path / name for name in app_names]
            if man_names:
                resources.man_paths[dep_name] = [venv_inspect_info.man_path / name for name in man_names]
            if completion_names:
                resources.completion_paths[dep_name] = [share_path / name for name in completion_names]
        dep_visited.setdefault(dep_name, set()).update(dep_req.extras)
        _dfs_package_resources(dep_dist, dep_req, venv_inspect_info, resources, dep_visited)


@dataclass(frozen=True, slots=True, kw_only=True)
class _DependencyResources:
    app_paths: dict[str, list[Path]]
    man_paths: dict[str, list[Path]]
    completion_paths: dict[str, list[Path]]


def _get_package_dependencies(dist: metadata.Distribution, extras: set[str], env: dict[str, str]) -> list[Requirement]:
    eval_env: Final[dict[str, str]] = env.copy()
    # an empty extra lets the markers that name no extra evaluate
    if not extras:
        extras.add("")
    dependencies: Final[list[Requirement]] = []
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


def _get_resources(
    dist: metadata.Distribution, bin_path: Path, man_path: Path
) -> tuple[list[str], list[str], list[str]]:
    entry_point_apps: Final[set[str]] = _get_apps_from_entry_points(dist, bin_path)
    dist_file_apps, dist_file_man_pages, dist_file_completions = _get_resources_from_dist_files(
        dist, bin_path, man_path
    )
    inst_file_apps, inst_file_man_pages, inst_file_completions = _get_resources_from_inst_files(
        dist, bin_path, man_path
    )
    return (
        sorted(entry_point_apps | dist_file_apps | inst_file_apps),
        sorted(dist_file_man_pages | inst_file_man_pages | _get_man_pages_from_editable_project(dist, man_path)),
        sorted(dist_file_completions | inst_file_completions),
    )


def _get_apps_from_entry_points(dist: metadata.Distribution, bin_path: Path) -> set[str]:
    if not _owns_entry_points(dist):
        return set()
    app_names: Final[set[str]] = set()
    for entry_point in dist.entry_points:
        if entry_point.group not in {"console_scripts", "gui_scripts"} or not is_file_name(entry_point.name):
            continue
        if (bin_path / entry_point.name).exists():
            app_names.add(entry_point.name)
        # Windows installs a script entry point as an .exe
        if WINDOWS and (bin_path / f"{entry_point.name}.exe").exists():
            app_names.add(f"{entry_point.name}.exe")
    return app_names


def _owns_entry_points(dist: metadata.Distribution) -> bool:
    # every wheel unpacks into one site-packages, so a dependency can plant entry_points.txt in this .dist-info
    if dist.read_text("RECORD") is None:
        return True
    return any(path.name == "entry_points.txt" and path.parent.suffix == ".dist-info" for path in dist.files or [])


def _get_resources_from_dist_files(
    dist: metadata.Distribution, bin_path: Path, man_path: Path
) -> tuple[set[str], set[str], set[str]]:
    app_names: Final[set[str]] = set()
    man_names: Final[set[str]] = set()
    completion_names: Final[set[str]] = set()
    # setup.py "scripts" (awscli ships its commands that way) appear here
    for path in dist.files or []:
        # apps and man pages sit above the distribution root (venv/bin, venv/Scripts), and skipping the rest is fast
        if Path(path).parts[0] != ".." or not is_file_name(path.name):
            continue

        dist_file_path: Final[Path] = Path(str(dist.locate_file(path)))
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


def _get_completion_name(file_path: Path, share_path: Path) -> str | None:
    # a wheel ships its completion scripts in the data scheme, which lands them beside the man pages under share/
    for section in COMPLETION_SECTIONS:
        if _same_file(file_path.parent, share_path / section):
            return str(section / file_path.name)
    return None


def _same_file(left: Path, right: Path) -> bool:
    try:
        return left.samefile(right)
    except OSError:
        return False


def _get_resources_from_inst_files(
    dist: metadata.Distribution, bin_path: Path, man_path: Path
) -> tuple[set[str], set[str], set[str]]:
    app_names: Final[set[str]] = set()
    man_names: Final[set[str]] = set()
    completion_names: Final[set[str]] = set()
    # only a legacy egg-info owns this file; next to a RECORD another wheel planted it, and importlib ignores it too
    inst_files: Final[str] = "" if dist.read_text("RECORD") is not None else dist.read_text("installed-files.txt") or ""
    for line in inst_files.splitlines():
        # Path.resolve() raises RuntimeError on a symlink loop before Python 3.13, os.path.realpath() does not
        inst_file_path: Final[Path] = Path(os.path.realpath(str(dist.locate_file(line.split(",")[0]))))
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


def _get_man_pages_from_editable_project(dist: metadata.Distribution, man_path: Path) -> set[str]:
    if (editable_root := _get_editable_project_root(dist)) is None:
        return set()
    # Path.resolve() raises RuntimeError on a symlink loop before Python 3.13, os.path.realpath() does not
    project_root: Final[Path] = Path(os.path.realpath(editable_root))

    man_names: Final[set[str]] = set()
    for target_dir, source_paths in _iter_editable_project_data_files(project_root):
        if (man_section := _get_man_section_from_data_files_target(target_dir)) is None:
            continue
        for source_path in source_paths:
            source: Final[Path] = project_root / source_path
            # a wheel can ship its own direct_url.json, so only files inside the project count as its man pages
            if not (resolved := Path(os.path.realpath(source))).is_relative_to(project_root) or not resolved.is_file():
                continue
            dest: Final[Path] = man_path / man_section / source.name
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(resolved, dest)
            except OSError as exc:
                _LOGGER.warning("Unable to copy editable man page %s to %s: %s", source, dest, exc)
                continue
            man_names.add(str(Path(man_section) / source.name))

    return man_names


def _get_editable_project_root(dist: metadata.Distribution) -> Path | None:
    if not (direct_url := dist.read_text("direct_url.json")):
        return None
    try:
        data: Final = json.loads(direct_url)
    except json.JSONDecodeError:
        return None

    if not isinstance(dir_info := data.get("dir_info", {}), dict) or not dir_info.get("editable"):
        return None

    if not isinstance(url := data.get("url"), str):
        return None
    if (parsed_url := urlparse(url)).scheme != "file":
        return None

    from urllib.request import url2pathname  # ruff:ignore[import-outside-top-level]  # pulls in http.client, slows startup

    return Path(url2pathname(f"//{parsed_url.netloc}{parsed_url.path}" if parsed_url.netloc else parsed_url.path))


def _iter_editable_project_data_files(project_root: Path) -> Iterator[tuple[str, list[str]]]:
    yield from _iter_pyproject_data_files(project_root)
    yield from _iter_setup_cfg_data_files(project_root)
    yield from _iter_setup_py_data_files(project_root)


def _iter_pyproject_data_files(project_root: Path) -> Iterator[tuple[str, list[str]]]:
    try:
        with (project_root / "pyproject.toml").open("rb") as file:
            pyproject_data: Final = tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError):
        return

    yield from _iter_normalized_data_files(pyproject_data.get("tool", {}).get("setuptools", {}).get("data-files", {}))


def _iter_normalized_data_files(data_files: object) -> Iterator[tuple[str, list[str]]]:
    items: Iterable[object]
    if isinstance(data_files, dict):
        items = data_files.items()
    elif isinstance(data_files, (list, tuple)):
        items = data_files
    else:
        return

    pair_length: Final[int] = 2
    for item in items:
        if not isinstance(item, (list, tuple)) or len(item) != pair_length:
            continue
        target_dir, source_paths = item
        if not isinstance(target_dir, str):
            continue
        if isinstance(source_paths, str):
            yield target_dir, [line.strip() for line in source_paths.splitlines() if line.strip()]
        elif isinstance(source_paths, (list, tuple)) and all(isinstance(path, str) for path in source_paths):
            yield target_dir, [path for path in source_paths if isinstance(path, str)]


def _iter_setup_cfg_data_files(project_root: Path) -> Iterator[tuple[str, list[str]]]:
    config: Final[configparser.ConfigParser] = configparser.ConfigParser(interpolation=None)
    try:
        config.read(project_root / "setup.cfg")
    except configparser.Error:
        return
    if not config.has_section("options.data_files"):
        return

    yield from _iter_normalized_data_files(dict(config.items("options.data_files")))


def _iter_setup_py_data_files(project_root: Path) -> Iterator[tuple[str, list[str]]]:
    try:
        tree: Final[ast.Module] = ast.parse((project_root / "setup.py").read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_setup_call(node):
            continue
        for keyword in node.keywords:
            if keyword.arg != "data_files":
                continue
            try:
                data_files: Final = ast.literal_eval(keyword.value)
            except (ValueError, SyntaxError):
                return
            yield from _iter_normalized_data_files(data_files)
            return


def _is_setup_call(node: ast.Call) -> bool:
    return (isinstance(node.func, ast.Name) and node.func.id == "setup") or (
        isinstance(node.func, ast.Attribute) and node.func.attr == "setup"
    )


def _get_man_section_from_data_files_target(target_dir: str) -> str | None:
    parts: Final[tuple[str, ...]] = PurePosixPath(target_dir.replace("\\", "/")).parts
    min_parts: Final[int] = 2
    if len(parts) < min_parts or parts[-2] != "man" or parts[-1] not in MAN_SECTIONS:
        return None
    return parts[-1]


def _windows_extra_app_paths(app_paths: list[Path]) -> list[Path]:
    # an editable app on Windows runs only with its *-script.py and *.exe.manifest companions in the same directory, so
    # they join app_paths while staying out of the listed apps
    app_paths_output: Final[list[Path]] = app_paths.copy()
    for app_path in app_paths:
        for companion_suffix in ("-script.py", ".exe.manifest"):
            if (companion := app_path.parent / f"{app_path.stem}{companion_suffix}").exists():
                app_paths_output.append(companion)
    return app_paths_output


@dataclass(frozen=True, slots=True, kw_only=True)
class VenvMetadata:
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
    unsupported_python: SpecifierSet | None


def list_not_required_packages(venv_python: Path) -> set[str]:
    venv_sys_path, venv_env, _ = fetch_info_in_venv(venv_python)
    return not_required_packages(venv_sys_path, venv_env)


def not_required_packages(sys_path: list[str], env: dict[str, str]) -> set[str]:
    # mirrors `pip list --not-required` from the installed metadata, so every backend reports the same packages, uv
    # included, which lacks the flag
    installed: Final[set[str]] = set()
    required: Final[set[str]] = set()
    for dist in metadata.distributions(path=sys_path):
        if (name := _distribution_name(dist)) is not None:
            installed.add(canonicalize_name(name))
        required.update(get_required_dependency_names(dist, env))
    return installed - required


def get_required_dependency_names(dist: metadata.Distribution, env: dict[str, str]) -> set[str]:
    # every declared extra counts, so a dependency only an extra pulls in stays required, and pipx does not report it
    # removable while the package declaring it is installed
    return {
        canonicalize_name(req.name)
        for req in _get_package_dependencies(dist, set(dist.metadata.get_all("Provides-Extra") or []), env)
    }


__all__ = [
    "VenvMetadata",
    "fetch_info_in_venv",
    "get_distributions_by_name",
    "get_required_dependency_names",
    "inspect_venv",
    "list_not_required_packages",
    "not_required_packages",
]
