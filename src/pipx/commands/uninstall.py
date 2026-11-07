from __future__ import annotations

__lazy_modules__ = ["pipx", "pipx.commands.common", "pipx.trash", "pipx.venv", "shutil"]

import logging
from dataclasses import dataclass
from shutil import which
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path

    from pipx.pipx_metadata_file import PackageInfo

from pipx import paths
from pipx.commands.common import (
    drop_copies_claimed_elsewhere,
    drop_links_taken_over,
    get_venv_package_infos,
    get_venv_resource_paths,
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
from pipx.result import OperationData, OperationError, OperationResult, OutputMessage
from pipx.trash import rmdir_via_trash, safe_unlink
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
    "uninstall",
    "uninstall_all",
]
