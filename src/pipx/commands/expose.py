from __future__ import annotations

__lazy_modules__ = ["pipx", "pipx.commands.common", "pipx.trash", "pipx.venv"]

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from pipx import paths
from pipx.commands.common import drop_copies_claimed_elsewhere, expose_package_resources, get_venv_resource_paths
from pipx.constants import COMPLETION_SECTIONS, MAN_SECTIONS, ExitCode
from pipx.result import OperationData, OperationError, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.trash import safe_unlink
from pipx.venv import Venv

if TYPE_CHECKING:
    from pathlib import Path

    from pipx.pipx_metadata_file import PackageInfo


def expose(venv_dir: Path, local_bin_dir: Path, local_man_dir: Path, *, verbose: bool) -> OperationResult[ExposureData]:
    return _set_exposure(venv_dir, local_bin_dir, local_man_dir, verbose=verbose, enabled=True)


def _set_exposure(
    venv_dir: Path,
    local_bin_dir: Path,
    local_man_dir: Path,
    *,
    verbose: bool,
    enabled: bool,
) -> OperationResult[ExposureData]:
    command: Final[tuple[str, ...]] = ("expose",) if enabled else ("unexpose",)
    if not venv_dir.is_dir():
        return _failure(command, venv_dir.name, f"pipx does not manage package {venv_dir.name}")

    venv: Final[Venv] = Venv(venv_dir, verbose=verbose)
    if venv.pipx_metadata.main_package.package is None:
        return _failure(command, venv.name, f"pipx cannot read metadata for package {venv.name}")
    if not enabled and not venv.pipx_metadata.exposure_enabled:
        return _success(command, venv.name, _ExposureStatus.UNEXPOSED, f"{venv.name}: already unexposed")

    if enabled:
        linked_before: Final[set[Path] | None] = (
            _exposed_resources(venv, local_bin_dir, local_man_dir) if venv.pipx_metadata.exposure_enabled else None
        )
        attempted: Final[int] = sum(
            len(package_metadata.app_paths_to_expose)
            + len(package_metadata.man_paths_to_expose)
            + len(package_metadata.completion_paths_to_expose)
            for package_metadata in venv.package_metadata.values()
        )
        collisions: Final[list[Path]] = [
            collision
            for package_metadata in venv.package_metadata.values()
            for collision in expose_package_resources(package_metadata, local_bin_dir, local_man_dir, force=False)
        ]
        venv.pipx_metadata.exposure_enabled = True
        venv.pipx_metadata.write()
        if collisions:
            return _collision_outcome(command, venv.name, collisions, exposed_any=len(collisions) < attempted)
        prefix: Final[str] = (
            "already " if _exposed_resources(venv, local_bin_dir, local_man_dir) == linked_before else ""
        )
        return _success(command, venv.name, _ExposureStatus.EXPOSED, f"{venv.name}: {prefix}exposed")

    for resource_path in drop_copies_claimed_elsewhere(
        _exposed_resources(venv, local_bin_dir, local_man_dir), venv.bin_path
    ):
        safe_unlink(resource_path)
    venv.pipx_metadata.exposure_enabled = False
    venv.pipx_metadata.write()
    return _success(command, venv.name, _ExposureStatus.UNEXPOSED, f"{venv.name}: unexposed")


def _failure(command: tuple[str, ...], environment: str, error: str) -> OperationResult[ExposureData]:
    return OperationResult(
        command=command,
        data=ExposureData(environments=()),
        messages=(OutputMessage(text=error, stream=OutputStream.STDERR, level=OutputLevel.ERROR),),
        exit_code=ExitCode(1),
        errors=(OperationError(code="environment_expose_failed", message=error, environment=environment),),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ExposureData(OperationData):
    environments: tuple[_EnvironmentExposure, ...]


def _success(
    command: tuple[str, ...], environment: str, status: _ExposureStatus, message: str
) -> OperationResult[ExposureData]:
    return OperationResult(
        command=command,
        data=ExposureData(environments=(_EnvironmentExposure(environment=environment, status=status),)),
        messages=(OutputMessage(text=message),),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class _EnvironmentExposure:
    environment: str
    status: _ExposureStatus


class _ExposureStatus(StrEnum):
    EXPOSED = "exposed"
    UNEXPOSED = "unexposed"


def _exposed_resources(venv: Venv, local_bin_dir: Path, local_man_dir: Path) -> set[Path]:
    package_infos: Final[tuple[PackageInfo, ...]] = tuple(venv.package_metadata.values())
    resource_paths = get_venv_resource_paths("app", venv.bin_path, local_bin_dir, package_infos)
    for man_section in MAN_SECTIONS:
        resource_paths |= get_venv_resource_paths(
            "man",
            venv.man_path / man_section,
            local_man_dir / man_section,
            package_infos,
        )
    for completion_section in COMPLETION_SECTIONS:
        resource_paths |= get_venv_resource_paths(
            "completion",
            venv.man_path.parent / completion_section,
            paths.CTX.completion_dir / completion_section,
            package_infos,
        )
    return resource_paths


def _collision_outcome(
    command: tuple[str, ...], environment: str, collisions: list[Path], *, exposed_any: bool
) -> OperationResult[ExposureData]:
    summary: Final[str] = (
        f"{environment}: skipped {len(collisions)} resource(s) already present in the target directory"
    )
    return OperationResult(
        command=command,
        data=ExposureData(
            environments=(_EnvironmentExposure(environment=environment, status=_ExposureStatus.EXPOSED),)
        ),
        messages=(OutputMessage(text=summary, stream=OutputStream.STDERR, level=OutputLevel.ERROR),),
        exit_code=ExitCode(1),
        errors=tuple(
            OperationError(
                code="environment_expose_conflict",
                message=f"{path} already exists and does not belong to {environment}",
                environment=environment,
            )
            for path in collisions
        ),
        succeeded=exposed_any,
    )


def unexpose(
    venv_dir: Path, local_bin_dir: Path, local_man_dir: Path, *, verbose: bool
) -> OperationResult[ExposureData]:
    return _set_exposure(venv_dir, local_bin_dir, local_man_dir, verbose=verbose, enabled=False)


__all__ = [
    "ExposureData",
    "expose",
    "unexpose",
]
