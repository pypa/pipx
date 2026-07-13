from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from pipx.commands.common import expose_package_resources
from pipx.commands.uninstall import _get_venv_resource_paths
from pipx.constants import MAN_SECTIONS, ExitCode
from pipx.result import OperationData, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.util import safe_unlink
from pipx.venv import Venv

if TYPE_CHECKING:
    from pathlib import Path


def expose(venv_dir: Path, local_bin_dir: Path, local_man_dir: Path, verbose: bool) -> OperationResult[ExposureData]:
    return _set_exposure(venv_dir, local_bin_dir, local_man_dir, verbose, enabled=True)


def unexpose(venv_dir: Path, local_bin_dir: Path, local_man_dir: Path, verbose: bool) -> OperationResult[ExposureData]:
    return _set_exposure(venv_dir, local_bin_dir, local_man_dir, verbose, enabled=False)


def _set_exposure(
    venv_dir: Path,
    local_bin_dir: Path,
    local_man_dir: Path,
    verbose: bool,
    *,
    enabled: bool,
) -> OperationResult[ExposureData]:
    command = "expose" if enabled else "unexpose"
    if not venv_dir.is_dir():
        return _failure(command, venv_dir.name, f"pipx does not manage package {venv_dir.name}")

    venv = Venv(venv_dir, verbose=verbose)
    if venv.pipx_metadata.main_package.package is None:
        return _failure(command, venv.name, f"pipx cannot read metadata for package {venv.name}")
    if venv.pipx_metadata.exposure_enabled == enabled:
        status = _ExposureStatus.EXPOSED if enabled else _ExposureStatus.UNEXPOSED
        return _success(command, venv.name, status, f"{venv.name}: already {status.value}")

    if enabled:
        for package_metadata in venv.package_metadata.values():
            expose_package_resources(package_metadata, local_bin_dir, local_man_dir, force=False)
        status = _ExposureStatus.EXPOSED
    else:
        _remove_resources(venv, local_bin_dir, local_man_dir)
        status = _ExposureStatus.UNEXPOSED
    venv.pipx_metadata.exposure_enabled = enabled
    venv.pipx_metadata.write()
    return _success(command, venv.name, status, f"{venv.name}: {status.value}")


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
    for resource_path in resource_paths:
        safe_unlink(resource_path)


def _success(command: str, environment: str, status: _ExposureStatus, message: str) -> OperationResult[ExposureData]:
    return OperationResult(
        command=command,
        data=ExposureData(environments=(_EnvironmentExposure(environment, status),), failures=()),
        messages=(OutputMessage(message),),
    )


def _failure(command: str, environment: str, error: str) -> OperationResult[ExposureData]:
    return OperationResult(
        command=command,
        data=ExposureData(environments=(), failures=(_FailedExposure(environment, error),)),
        messages=(OutputMessage(error, stream=OutputStream.STDERR, level=OutputLevel.ERROR),),
        exit_code=ExitCode(1),
    )


class _ExposureStatus(str, Enum):
    EXPOSED = "exposed"
    UNEXPOSED = "unexposed"


@dataclass(frozen=True)
class _EnvironmentExposure:
    environment: str
    status: _ExposureStatus


@dataclass(frozen=True)
class _FailedExposure:
    environment: str
    error: str


@dataclass(frozen=True)
class ExposureData(OperationData):
    environments: tuple[_EnvironmentExposure, ...]
    failures: tuple[_FailedExposure, ...]


__all__ = [
    "ExposureData",
    "expose",
    "unexpose",
]
