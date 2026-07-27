from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Final

from pipx import paths
from pipx.commands.common import expose_package_resources
from pipx.commands.uninstall import _get_venv_resource_paths
from pipx.constants import COMPLETION_SECTIONS, MAN_SECTIONS, ExitCode
from pipx.result import OperationData, OperationError, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.util import safe_unlink
from pipx.venv import Venv

if TYPE_CHECKING:
    from pathlib import Path


def expose(venv_dir: Path, local_bin_dir: Path, local_man_dir: Path, *, verbose: bool) -> OperationResult[ExposureData]:
    return _set_exposure(venv_dir, local_bin_dir, local_man_dir, verbose=verbose, enabled=True)


def unexpose(
    venv_dir: Path, local_bin_dir: Path, local_man_dir: Path, *, verbose: bool
) -> OperationResult[ExposureData]:
    return _set_exposure(venv_dir, local_bin_dir, local_man_dir, verbose=verbose, enabled=False)


def _set_exposure(
    venv_dir: Path,
    local_bin_dir: Path,
    local_man_dir: Path,
    *,
    verbose: bool,
    enabled: bool,
) -> OperationResult[ExposureData]:
    command = ("expose",) if enabled else ("unexpose",)
    if not venv_dir.is_dir():
        return _failure(command, venv_dir.name, f"pipx does not manage package {venv_dir.name}")

    venv = Venv(venv_dir, verbose=verbose)
    if venv.pipx_metadata.main_package.package is None:
        return _failure(command, venv.name, f"pipx cannot read metadata for package {venv.name}")
    if venv.pipx_metadata.exposure_enabled == enabled:
        status = _ExposureStatus.EXPOSED if enabled else _ExposureStatus.UNEXPOSED
        return _success(command, venv.name, status, f"{venv.name}: already {status.value}")

    if enabled:
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
        return _success(command, venv.name, _ExposureStatus.EXPOSED, f"{venv.name}: exposed")

    _remove_resources(venv, local_bin_dir, local_man_dir)
    venv.pipx_metadata.exposure_enabled = False
    venv.pipx_metadata.write()
    return _success(command, venv.name, _ExposureStatus.UNEXPOSED, f"{venv.name}: unexposed")


def _remove_resources(venv: Venv, local_bin_dir: Path, local_man_dir: Path) -> None:
    package_infos = tuple(venv.package_metadata.values())
    resource_paths = _get_venv_resource_paths("app", venv.bin_path, local_bin_dir, package_infos)
    for man_section in MAN_SECTIONS:
        resource_paths |= _get_venv_resource_paths(
            "man",
            venv.man_path / man_section,
            local_man_dir / man_section,
            package_infos,
        )
    for completion_section in COMPLETION_SECTIONS:
        resource_paths |= _get_venv_resource_paths(
            "completion",
            venv.man_path.parent / completion_section,
            paths.ctx.completion_dir / completion_section,
            package_infos,
        )
    for resource_path in resource_paths:
        safe_unlink(resource_path)


def _success(
    command: tuple[str, ...], environment: str, status: _ExposureStatus, message: str
) -> OperationResult[ExposureData]:
    return OperationResult(
        command=command,
        data=ExposureData(environments=(_EnvironmentExposure(environment, status),)),
        messages=(OutputMessage(message),),
    )


def _collision_outcome(
    command: tuple[str, ...], environment: str, collisions: list[Path], *, exposed_any: bool
) -> OperationResult[ExposureData]:
    summary: Final[str] = (
        f"{environment}: skipped {len(collisions)} resource(s) already present in the target directory"
    )
    return OperationResult(
        command=command,
        data=ExposureData(environments=(_EnvironmentExposure(environment, _ExposureStatus.EXPOSED),)),
        messages=(OutputMessage(summary, stream=OutputStream.STDERR, level=OutputLevel.ERROR),),
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


def _failure(command: tuple[str, ...], environment: str, error: str) -> OperationResult[ExposureData]:
    return OperationResult(
        command=command,
        data=ExposureData(environments=()),
        messages=(OutputMessage(error, stream=OutputStream.STDERR, level=OutputLevel.ERROR),),
        exit_code=ExitCode(1),
        errors=(OperationError(code="environment_expose_failed", message=error, environment=environment),),
    )


class _ExposureStatus(str, Enum):
    EXPOSED = "exposed"
    UNEXPOSED = "unexposed"


@dataclass(frozen=True)
class _EnvironmentExposure:
    environment: str
    status: _ExposureStatus


@dataclass(frozen=True)
class ExposureData(OperationData):
    environments: tuple[_EnvironmentExposure, ...]


__all__ = [
    "ExposureData",
    "expose",
    "unexpose",
]
