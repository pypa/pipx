from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Final

from packaging.utils import canonicalize_name

from pipx.colors import bold
from pipx.commands.common import add_suffix
from pipx.commands.inject import (
    InjectionData,
    InjectionFailure,
    InjectionPackage,
    InjectionStatus,
)
from pipx.commands.uninstall import (
    _get_package_bin_dir_app_paths,
    _get_package_man_paths,
)
from pipx.constants import (
    EXIT_CODE_OK,
    EXIT_CODE_UNINJECT_ERROR,
    MAN_SECTIONS,
)
from pipx.emojis import stars
from pipx.result import OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.util import pipx_wrap, safe_unlink
from pipx.venv import Venv
from pipx.venv_inspect import fetch_info_in_venv, get_distributions_by_name, get_required_dependency_names

if TYPE_CHECKING:
    from importlib import metadata

    from pipx.pipx_metadata_file import PackageInfo

logger = logging.getLogger(__name__)


def uninject(
    venv_dir: Path,
    dependencies: list[str],
    *,
    local_bin_dir: Path,
    local_man_dir: Path,
    leave_deps: bool,
    verbose: bool,
) -> OperationResult[InjectionData]:
    if not venv_dir.exists() or next(venv_dir.iterdir(), None) is None:
        return _uninject_failure(
            venv_dir.name,
            None,
            f"Virtual environment {venv_dir.name} does not exist.",
            stream=OutputStream.STDERR,
        )

    venv: Final[Venv] = Venv(venv_dir, verbose=verbose)

    if not venv.package_metadata:
        return _uninject_failure(
            venv.name,
            None,
            pipx_wrap(
                f"""
                Can't uninject from Virtual Environment {venv_dir.name!r}.
                {venv_dir.name!r} has missing internal pipx metadata.
                It was likely installed using a pipx version before 0.15.0.0.
                Please uninstall and install {venv_dir.name!r} manually to fix.
                """
            ),
            stream=OutputStream.STDERR,
        )

    failures: Final[list[InjectionFailure]] = []
    messages: Final[list[OutputMessage]] = []
    packages: Final[list[InjectionPackage]] = []
    for dep in dependencies:
        result: OperationResult[InjectionData] = uninject_dep(
            venv,
            dep,
            local_bin_dir=local_bin_dir,
            local_man_dir=local_man_dir,
            leave_deps=leave_deps,
        )
        failures.extend(result.data.failures)
        messages.extend(result.messages)
        packages.extend(result.data.packages)

    return OperationResult(
        command="uninject",
        data=InjectionData(packages=tuple(packages), skipped=(), failures=tuple(failures)),
        messages=tuple(messages),
        exit_code=EXIT_CODE_UNINJECT_ERROR if failures else EXIT_CODE_OK,
    )


def uninject_dep(
    venv: Venv,
    package_name: str,
    *,
    local_bin_dir: Path,
    local_man_dir: Path,
    leave_deps: bool = False,
) -> OperationResult[InjectionData]:
    package_name = canonicalize_name(package_name)

    if package_name == venv.pipx_metadata.main_package.package:
        return _uninject_failure(
            venv.name,
            package_name,
            pipx_wrap(
                f"""
                {package_name} is the main package of {venv.root.name}
                venv. Use `pipx uninstall {venv.root.name}` to uninstall instead of uninject.
                """,
                subsequent_indent=" " * 4,
            ),
        )

    if package_name not in venv.pipx_metadata.injected_packages:
        return _uninject_failure(
            venv.name,
            package_name,
            f"{package_name} is not in the {venv.root.name} venv. Skipping.",
        )

    package: Final[PackageInfo] = venv.package_metadata[package_name]
    need_app_uninstall: Final[bool] = package.include_apps

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
                safe_unlink(path)
            except FileNotFoundError:
                logger.info(f"tried to remove but couldn't find {path}")
            else:
                logger.info(f"removed file {path}")

    return OperationResult(
        command="uninject",
        data=InjectionData(
            packages=(
                InjectionPackage(
                    environment=venv.name,
                    package=f"{package.package}{package.suffix}",
                    version=package.package_version,
                    status=InjectionStatus.UNINJECTED,
                    location=str(venv.root),
                ),
            ),
            skipped=(),
            failures=(),
        ),
        messages=(
            OutputMessage(
                f"Uninjected package {bold(package_name)}{deps_string} from venv {bold(venv.root.name)} {stars}"
            ),
        ),
    )


def _uninject_failure(
    environment: str,
    package: str | None,
    error: str,
    *,
    stream: OutputStream = OutputStream.LOG,
) -> OperationResult[InjectionData]:
    return OperationResult(
        command="uninject",
        data=InjectionData(packages=(), skipped=(), failures=(InjectionFailure(environment, package, error),)),
        messages=(OutputMessage(error, stream=stream, level=OutputLevel.ERROR),),
        exit_code=EXIT_CODE_UNINJECT_ERROR,
    )


def get_include_resource_paths(package_name: str, venv: Venv, local_bin_dir: Path, local_man_dir: Path) -> set[Path]:
    bin_dir_app_paths = _get_package_bin_dir_app_paths(venv.package_metadata[package_name], venv.bin_path, local_bin_dir)
    man_paths = set()
    for man_section in MAN_SECTIONS:
        man_paths |= _get_package_man_paths(
            venv.package_metadata[package_name],
            venv.man_path / man_section,
            local_man_dir / man_section,
        )

    pkg_metadata = venv.package_metadata[package_name]
    all_apps = {add_suffix(app, pkg_metadata.suffix) for app in pkg_metadata.apps_to_expose}
    all_man_pages = set(pkg_metadata.man_pages_to_expose)

    need_to_remove = set()
    for bin_dir_app_path in bin_dir_app_paths:
        if bin_dir_app_path.name in all_apps:
            need_to_remove.add(bin_dir_app_path)
    for man_path in man_paths:
        path = Path(man_path.parent.name) / man_path.name
        if str(path) in all_man_pages:
            need_to_remove.add(man_path)

    return need_to_remove


def _get_remaining_dependencies(venv: Venv, excluded_package: str) -> set[str]:
    venv_sys_path, venv_env, _ = fetch_info_in_venv(venv.python_path)
    distributions = get_distributions_by_name(venv_sys_path)

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
    distributions: dict[str, metadata.Distribution],
    env: dict[str, str],
    visited: set[str] | None = None,
) -> set[str]:
    if visited is None:
        visited = set()
    canonical = canonicalize_name(package_name)
    if canonical in visited:
        return visited
    visited.add(canonical)
    if dist := distributions.get(canonical):
        for dep_name in get_required_dependency_names(dist, env):
            _collect_transitive_deps(dep_name, distributions, env, visited)
    return visited


__all__ = [
    "uninject",
]
