import logging
import os
from importlib import metadata
from pathlib import Path
from typing import Optional

from packaging.utils import canonicalize_name

from pipx.colors import bold
from pipx.commands.uninstall import (
    _get_package_bin_dir_app_paths,
    _get_package_man_paths,
)
from pipx.constants import (
    EXIT_CODE_OK,
    EXIT_CODE_UNINJECT_ERROR,
    MAN_SECTIONS,
    ExitCode,
)
from pipx.emojis import stars
from pipx.util import PipxError, pipx_wrap
from pipx.venv import Venv
from pipx.venv_inspect import fetch_info_in_venv, get_dist, get_package_dependencies

logger = logging.getLogger(__name__)


def uninject(
    venv_dir: Path,
    dependencies: list[str],
    *,
    local_bin_dir: Path,
    local_man_dir: Path,
    leave_deps: bool,
    verbose: bool,
) -> ExitCode:
    """Returns pipx exit code"""

    if not venv_dir.exists() or next(venv_dir.iterdir(), None) is None:
        raise PipxError(f"Virtual environment {venv_dir.name} does not exist.")

    venv = Venv(venv_dir, verbose=verbose)

    if not venv.package_metadata:
        raise PipxError(
            f"""
            Can't uninject from Virtual Environment {venv_dir.name!r}.
            {venv_dir.name!r} has missing internal pipx metadata.
            It was likely installed using a pipx version before 0.15.0.0.
            Please uninstall and install {venv_dir.name!r} manually to fix.
            """
        )

    all_success = True
    for dep in dependencies:
        all_success &= uninject_dep(
            venv,
            dep,
            local_bin_dir=local_bin_dir,
            local_man_dir=local_man_dir,
            leave_deps=leave_deps,
        )

    if all_success:
        return EXIT_CODE_OK
    else:
        return EXIT_CODE_UNINJECT_ERROR


def uninject_dep(
    venv: Venv,
    package_name: str,
    *,
    local_bin_dir: Path,
    local_man_dir: Path,
    leave_deps: bool = False,
) -> bool:
    package_name = canonicalize_name(package_name)

    if package_name == venv.pipx_metadata.main_package.package:
        logger.warning(
            pipx_wrap(
                f"""
            {package_name} is the main package of {venv.root.name}
            venv. Use `pipx uninstall {venv.root.name}` to uninstall instead of uninject.
            """,
                subsequent_indent=" " * 4,
            )
        )
        return False

    if package_name not in venv.pipx_metadata.injected_packages:
        logger.warning(f"{package_name} is not in the {venv.root.name} venv. Skipping.")
        return False

    need_app_uninstall = venv.package_metadata[package_name].include_apps

    new_resource_paths = get_include_resource_paths(package_name, venv, local_bin_dir, local_man_dir)

    if not leave_deps:
        orig_not_required_packages = venv.list_installed_packages(not_required=True)
        logger.info(f"Original not required packages: {orig_not_required_packages}")

    venv.uninstall_package(package=package_name, was_injected=True)

    if not leave_deps:
        new_not_required_packages = venv.list_installed_packages(not_required=True)
        logger.info(f"New not required packages: {new_not_required_packages}")

        deps_of_uninstalled = new_not_required_packages - orig_not_required_packages
        if deps_of_uninstalled:
            remaining_deps = _get_remaining_dependencies(venv, package_name)
            deps_of_uninstalled -= remaining_deps
            logger.info(f"Dependencies of uninstalled package: {deps_of_uninstalled}")

        for dep_package_name in deps_of_uninstalled:
            venv.uninstall_package(package=dep_package_name, was_injected=False)

        deps_string = " and its dependencies"
    else:
        deps_string = ""

    if need_app_uninstall:
        for path in new_resource_paths:
            try:
                os.unlink(path)
            except FileNotFoundError:
                logger.info(f"tried to remove but couldn't find {path}")
            else:
                logger.info(f"removed file {path}")

    print(f"Uninjected package {bold(package_name)}{deps_string} from venv {bold(venv.root.name)} {stars}")
    return True


def get_include_resource_paths(package_name: str, venv: Venv, local_bin_dir: Path, local_man_dir: Path) -> set[Path]:
    bin_dir_app_paths = _get_package_bin_dir_app_paths(
        venv, venv.package_metadata[package_name], venv.bin_path, local_bin_dir
    )
    man_paths = set()
    for man_section in MAN_SECTIONS:
        man_paths |= _get_package_man_paths(
            venv,
            venv.package_metadata[package_name],
            venv.man_path / man_section,
            local_man_dir / man_section,
        )

    need_to_remove = set()
    for bin_dir_app_path in bin_dir_app_paths:
        if bin_dir_app_path.name in venv.package_metadata[package_name].apps:
            need_to_remove.add(bin_dir_app_path)
    for man_path in man_paths:
        path = Path(man_path.parent.name) / man_path.name
        if str(path) in venv.package_metadata[package_name].man_pages:
            need_to_remove.add(path)

    return need_to_remove


def _get_remaining_dependencies(venv: Venv, excluded_package: str) -> set[str]:
    venv_sys_path, venv_env, _ = fetch_info_in_venv(venv.python_path)
    distributions = tuple(metadata.distributions(path=venv_sys_path))

    remaining_deps: set[str] = set()
    remaining_packages: list[str] = [
        name
        for name in [venv.pipx_metadata.main_package.package] + list(venv.pipx_metadata.injected_packages)
        if name is not None and name != excluded_package
    ]
    for pkg_name in remaining_packages:
        remaining_deps |= _collect_transitive_deps(pkg_name, distributions, venv_env)

    return remaining_deps


def _collect_transitive_deps(
    package_name: str,
    distributions: tuple[metadata.Distribution, ...],
    env: dict[str, str],
    visited: Optional[set[str]] = None,
) -> set[str]:
    if visited is None:
        visited = set()
    canonical = canonicalize_name(package_name)
    if canonical in visited:
        return visited
    visited.add(canonical)
    if dist := get_dist(package_name, distributions):
        for dep_req in get_package_dependencies(dist, set(), env):
            _collect_transitive_deps(dep_req.name, distributions, env, visited)
    return visited
