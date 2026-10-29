from __future__ import annotations

__lazy_modules__ = ["pipx", "pipx.commands.common", "pipx.pipx_metadata_file", "pipx.util", "pipx.venv", "shutil"]

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
    can_symlink,
    drop_copies_claimed_elsewhere,
    drop_links_taken_over,
    get_exposed_man_paths_for_package,
    get_exposed_paths_for_package,
    group_app_paths,
    group_resource_paths,
    reuse_resource_dir_scans,
)
from pipx.constants import (
    COMPLETION_SECTIONS,
    EXIT_CODE_OK,
    EXIT_CODE_UNINSTALL_ERROR,
    EXIT_CODE_UNINSTALL_VENV_NONEXISTENT,
    MAN_SECTIONS,
)
from pipx.emojis import HAZARD, SLEEP, STARS
from pipx.pipx_metadata_file import PackageInfo
from pipx.result import OperationData, OperationError, OperationResult, OutputMessage
from pipx.util import PipxError, rmdir_via_trash, safe_unlink
from pipx.venv import Venv, VenvContainer

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def uninstall_all(
    venv_container: VenvContainer,
    local_bin_dir: Path,
    local_man_dir: Path,
    *,
    verbose: bool,
) -> OperationResult[UninstallData]:
    errors: Final[list[OperationError]] = []
    messages: Final[list[OutputMessage]] = []
    packages: Final[list[_UninstalledPackage]] = []
    with reuse_resource_dir_scans():
        for venv_dir in venv_container.iter_venv_dirs():
            with venv_container.venv_lock(venv_dir):
                result: Final = uninstall(venv_dir, local_bin_dir, local_man_dir, verbose=verbose)
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
    *,
    verbose: bool,
) -> OperationResult[UninstallData]:
    if not venv_dir.exists():
        messages: Final[list[OutputMessage]] = [OutputMessage(text=f"Nothing to uninstall for {venv_dir.name} {SLEEP}")]
        if app := which(venv_dir.name):
            messages.append(
                OutputMessage(text=f"{HAZARD}  Note: '{app}' still exists on your system and is on your PATH")
            )
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

    venv: Final[Venv] = Venv(venv_dir, verbose=verbose)
    package_infos: Final[tuple[PackageInfo, ...] | None] = get_venv_package_infos(venv)
    resource_paths = get_venv_resource_paths("app", venv.bin_path, local_bin_dir, package_infos)
    for man_section in MAN_SECTIONS:
        resource_paths |= get_venv_resource_paths(
            "man", venv.man_path / man_section, local_man_dir / man_section, package_infos
        )
    for completion_section in COMPLETION_SECTIONS:
        resource_paths |= get_venv_resource_paths(
            "completion",
            venv.man_path.parent / completion_section,
            paths.CTX.completion_dir / completion_section,
            package_infos,
        )

    for path in drop_links_taken_over(drop_copies_claimed_elsewhere(resource_paths, venv.bin_path), venv_dir):
        _remove_resource(path)

    package_info: Final[PackageInfo | None] = next(
        (package_info for package_info in package_infos or () if package_info.package == venv.main_package_name),
        None,
    )
    # a removal killed halfway could drop the record but keep the package, which reinstall reads as a venv from pipx
    # before 0.15
    rmdir_via_trash(venv_dir)
    return OperationResult(
        command=("uninstall",),
        data=UninstallData(
            packages=(
                _UninstalledPackage(
                    environment=venv.name,
                    package=str(package_info.package) if package_info is not None else venv.name,
                    version=None if package_info is None else package_info.package_version or None,
                    location=str(venv.root),
                ),
            )
        ),
        messages=(OutputMessage(text=f"uninstalled {venv.name}! {STARS}"),),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class UninstallData(OperationData):
    packages: tuple[_UninstalledPackage, ...]


def get_venv_package_infos(venv: Venv) -> tuple[PackageInfo, ...] | None:
    if venv.pipx_metadata.main_package.package is not None:
        return tuple(venv.package_metadata.values())
    if not venv.python_path.is_file():
        return None
    try:
        venv_metadata: Final[VenvMetadata] = venv.get_venv_metadata_for_package(venv.root.name, set())
    except PipxError as error:
        # an environment that cannot report its packages is still removable, from the links that point into it
        _LOGGER.warning("%s  Unable to inspect %s, removing it anyway: %s", HAZARD, venv.name, error)
        return None
    return (
        PackageInfo(
            package=venv.root.name,
            package_or_url="",
            pip_args=[],
            include_apps=True,
            include_dependencies=False,
            apps=venv_metadata.apps,
            app_paths=venv_metadata.app_paths,
            apps_of_dependencies=venv_metadata.apps_of_dependencies,
            app_paths_of_dependencies=venv_metadata.app_paths_of_dependencies,
            man_pages=venv_metadata.man_pages,
            man_paths=venv_metadata.man_paths,
            man_pages_of_dependencies=venv_metadata.man_pages_of_dependencies,
            man_paths_of_dependencies=venv_metadata.man_paths_of_dependencies,
            package_version=venv_metadata.package_version,
            suffix="",
        ),
    )


def get_venv_resource_paths(
    resource_type: Literal["app", "man", "completion"],
    venv_resource_path: Path,
    local_resource_dir: Path,
    package_infos: tuple[PackageInfo, ...] | None,
) -> set[Path]:
    if package_infos is not None:
        get_package_resource_paths: Final[Callable[[PackageInfo, Path, Path], set[Path]]] = {
            "app": get_package_bin_dir_app_paths,
            "man": get_package_man_paths,
            "completion": get_package_completion_paths,
        }[resource_type]
        return set().union(
            *(
                get_package_resource_paths(package_info, venv_resource_path, local_resource_dir)
                for package_info in package_infos
            )
        )

    # without metadata, pipx infers ownership from link targets
    if not local_resource_dir.is_dir() or not can_symlink(local_resource_dir):
        return set()
    return get_exposed_paths_for_package(venv_resource_path, local_resource_dir)


def get_package_bin_dir_app_paths(package_info: PackageInfo, venv_bin_path: Path, local_bin_dir: Path) -> set[Path]:
    return get_exposed_paths_for_package(venv_bin_path, local_bin_dir, group_app_paths((package_info,)))


def get_package_man_paths(package_info: PackageInfo, venv_man_path: Path, local_man_dir: Path) -> set[Path]:
    return get_exposed_man_paths_for_package(venv_man_path, local_man_dir, package_info.man_paths_to_expose)


def get_package_completion_paths(
    package_info: PackageInfo,
    venv_completion_path: Path,
    local_completion_dir: Path,
) -> set[Path]:
    return get_exposed_paths_for_package(
        venv_completion_path,
        local_completion_dir,
        group_resource_paths((path.name, path) for path in package_info.completion_paths_to_expose),
    )


def _remove_resource(path: Path) -> None:
    try:
        safe_unlink(path)
    except FileNotFoundError:
        _LOGGER.info("pipx did not find resource %s", path)
    else:
        _LOGGER.info("pipx removed resource %s", path)


@dataclass(frozen=True, slots=True, kw_only=True)
class _UninstalledPackage:
    environment: str
    package: str
    version: str | None
    location: str


__all__ = [
    "UninstallData",
    "get_package_bin_dir_app_paths",
    "get_package_completion_paths",
    "get_package_man_paths",
    "get_venv_package_infos",
    "get_venv_resource_paths",
    "uninstall",
    "uninstall_all",
]
