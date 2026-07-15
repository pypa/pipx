from __future__ import annotations

import logging
from dataclasses import dataclass
from shutil import which
from typing import TYPE_CHECKING, Final, Literal

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from pipx.venv_inspect import VenvMetadata

from pipx import paths
from pipx.commands.common import (
    add_suffix,
    can_symlink,
    get_exposed_man_paths_for_package,
    get_exposed_paths_for_package,
    group_resource_paths,
)
from pipx.constants import (
    COMPLETION_SECTIONS,
    EXIT_CODE_OK,
    EXIT_CODE_UNINSTALL_ERROR,
    EXIT_CODE_UNINSTALL_VENV_NONEXISTENT,
    MAN_SECTIONS,
)
from pipx.emojis import hazard, sleep, stars
from pipx.pipx_metadata_file import PackageInfo
from pipx.result import OperationData, OperationError, OperationResult, OutputMessage
from pipx.util import rmdir, safe_unlink
from pipx.venv import Venv, VenvContainer

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def uninstall_all(
    venv_container: VenvContainer,
    local_bin_dir: Path,
    local_man_dir: Path,
    verbose: bool,
) -> OperationResult[UninstallData]:
    errors: list[OperationError] = []
    messages: list[OutputMessage] = []
    packages: list[_UninstalledPackage] = []
    for venv_dir in venv_container.iter_venv_dirs():
        with venv_container.venv_lock(venv_dir):
            result = uninstall(venv_dir, local_bin_dir, local_man_dir, verbose)
        errors.extend(result.errors)
        messages.extend(result.messages)
        packages.extend(result.data.packages)

    return OperationResult(
        command=("uninstall-all",),
        data=UninstallData(
            packages=tuple(sorted(packages, key=lambda package: package.environment)),
        ),
        messages=tuple(messages),
        exit_code=EXIT_CODE_UNINSTALL_ERROR if errors else EXIT_CODE_OK,
        errors=tuple(sorted(errors, key=lambda error: error.environment or "")),
        succeeded=bool(packages),
    )


def uninstall(
    venv_dir: Path,
    local_bin_dir: Path,
    local_man_dir: Path,
    verbose: bool,
) -> OperationResult[UninstallData]:
    if not venv_dir.exists():
        messages = [OutputMessage(f"Nothing to uninstall for {venv_dir.name} {sleep}")]
        if app := which(venv_dir.name):
            messages.append(OutputMessage(f"{hazard}  Note: '{app}' still exists on your system and is on your PATH"))
        return OperationResult(
            command=("uninstall",),
            data=UninstallData(packages=()),
            messages=tuple(messages),
            exit_code=EXIT_CODE_UNINSTALL_VENV_NONEXISTENT,
            errors=(
                OperationError(
                    code="environment_uninstall_failed",
                    message=f"Nothing to uninstall for {venv_dir.name}.",
                    environment=venv_dir.name,
                ),
            ),
        )

    venv = Venv(venv_dir, verbose=verbose)
    package_infos = _get_venv_package_infos(venv)
    resource_paths = _get_venv_resource_paths("app", venv.bin_path, local_bin_dir, package_infos)
    for man_section in MAN_SECTIONS:
        resource_paths |= _get_venv_resource_paths(
            "man", venv.man_path / man_section, local_man_dir / man_section, package_infos
        )
    for completion_section in COMPLETION_SECTIONS:
        resource_paths |= _get_venv_resource_paths(
            "completion",
            venv.man_path.parent / completion_section,
            paths.ctx.completion_dir / completion_section,
            package_infos,
        )

    for path in resource_paths:
        try:
            safe_unlink(path)
        except FileNotFoundError:
            _LOGGER.info("pipx did not find resource %s", path)
        else:
            _LOGGER.info("pipx removed resource %s", path)

    package_info = next(
        (package_info for package_info in package_infos or () if package_info.package == venv.main_package_name),
        None,
    )
    package = _UninstalledPackage(
        environment=venv.name,
        package=str(package_info.package) if package_info is not None else venv.name,
        version=None if package_info is None else package_info.package_version or None,
        location=str(venv.root),
    )
    rmdir(venv_dir)
    return OperationResult(
        command=("uninstall",),
        data=UninstallData(packages=(package,)),
        messages=(OutputMessage(f"uninstalled {venv.name}! {stars}"),),
    )


@dataclass(frozen=True)
class _UninstalledPackage:
    environment: str
    package: str
    version: str | None
    location: str


@dataclass(frozen=True)
class UninstallData(OperationData):
    packages: tuple[_UninstalledPackage, ...]


def _get_venv_package_infos(venv: Venv) -> tuple[PackageInfo, ...] | None:
    if venv.pipx_metadata.main_package.package is not None:
        return tuple(venv.package_metadata.values())
    if not venv.python_path.is_file():
        return None
    venv_metadata = venv.get_venv_metadata_for_package(venv.root.name, set())
    return (_venv_metadata_to_package_info(venv_metadata, venv.root.name),)


def _venv_metadata_to_package_info(
    venv_metadata: VenvMetadata,
    package_name: str,
    package_or_url: str = "",
    pip_args: list[str] | None = None,
    include_apps: bool = True,
    include_dependencies: bool = False,
    suffix: str = "",
) -> PackageInfo:
    if pip_args is None:
        pip_args = []

    return PackageInfo(
        package=package_name,
        package_or_url=package_or_url,
        pip_args=pip_args,
        include_apps=include_apps,
        include_dependencies=include_dependencies,
        apps=venv_metadata.apps,
        app_paths=venv_metadata.app_paths,
        apps_of_dependencies=venv_metadata.apps_of_dependencies,
        app_paths_of_dependencies=venv_metadata.app_paths_of_dependencies,
        man_pages=venv_metadata.man_pages,
        man_paths=venv_metadata.man_paths,
        man_pages_of_dependencies=venv_metadata.man_pages_of_dependencies,
        man_paths_of_dependencies=venv_metadata.man_paths_of_dependencies,
        package_version=venv_metadata.package_version,
        suffix=suffix,
    )


def _get_venv_resource_paths(
    resource_type: Literal["app", "man", "completion"],
    venv_resource_path: Path,
    local_resource_dir: Path,
    package_infos: tuple[PackageInfo, ...] | None,
) -> set[Path]:
    get_package_resource_paths: Callable[[PackageInfo, Path, Path], set[Path]] = {
        "app": _get_package_bin_dir_app_paths,
        "man": _get_package_man_paths,
        "completion": _get_package_completion_paths,
    }[resource_type]
    if package_infos is not None:
        return set().union(
            *(
                get_package_resource_paths(package_info, venv_resource_path, local_resource_dir)
                for package_info in package_infos
            )
        )

    # Without metadata, pipx infers ownership from link targets.
    if not local_resource_dir.is_dir() or not can_symlink(local_resource_dir):
        return set()
    return get_exposed_paths_for_package(venv_resource_path, local_resource_dir)


def _get_package_bin_dir_app_paths(package_info: PackageInfo, venv_bin_path: Path, local_bin_dir: Path) -> set[Path]:
    return get_exposed_paths_for_package(
        venv_bin_path,
        local_bin_dir,
        group_resource_paths(
            (add_suffix(path.name, package_info.suffix), path) for path in package_info.app_paths_to_expose
        ),
    )


def _get_package_man_paths(package_info: PackageInfo, venv_man_path: Path, local_man_dir: Path) -> set[Path]:
    return get_exposed_man_paths_for_package(venv_man_path, local_man_dir, package_info.man_paths_to_expose)


def _get_package_completion_paths(
    package_info: PackageInfo,
    venv_completion_path: Path,
    local_completion_dir: Path,
) -> set[Path]:
    return get_exposed_paths_for_package(
        venv_completion_path,
        local_completion_dir,
        group_resource_paths((path.name, path) for path in package_info.completion_paths_to_expose),
    )


__all__ = [
    "UninstallData",
    "_get_package_bin_dir_app_paths",
    "_get_package_man_paths",
    "_get_venv_package_infos",
    "_get_venv_resource_paths",
    "uninstall",
    "uninstall_all",
]
