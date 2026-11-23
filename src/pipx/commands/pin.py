from __future__ import annotations

from pipx.colors import BOLD
from pipx.constants import ExitCode
from pipx.emojis import SLEEP

__lazy_modules__ = ["packaging.utils", "pipx.pipx_metadata_file"]

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import TYPE_CHECKING, Final, NamedTuple

from packaging.utils import canonicalize_name

from pipx.pipx_metadata_file import PipxMetadata
from pipx.result import OperationData, OperationError, OperationResult, OutputLevel, OutputMessage, OutputStream

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from pipx.pipx_metadata_file import PackageInfo


def pin(
    venv_dir: Path,
    skip: Sequence[str],
    *,
    injected_only: bool,
) -> OperationResult[PinData]:
    """Pin the packages of an environment so that upgrades skip them.

    :param venv_dir: the directory of the environment.
    :param skip: the packages to leave unpinned.
    :param injected_only: pin only the injected packages, not the main package.
    :returns: the result listing the pinned and skipped packages.
    """
    metadata: Final[PipxMetadata] = PipxMetadata(venv_dir)
    if (main_name := metadata.main_package.package) is None:
        return _missing_result(("pin",), venv_dir.name)

    environment = _environment_name(metadata, main_name)
    changes = (
        _pin_requested(metadata, environment, skip)
        if injected_only or skip
        else _pin_all(metadata, environment, main_name)
    )
    messages: Final[list[OutputMessage]] = changes.messages
    if changes.packages:
        metadata.write(raise_on_error=True)
        messages.append(_summary_message(environment, _PinStatus.PINNED, len(changes.packages)))
        messages.extend(OutputMessage(text=f"  - {package.package} {package.version}") for package in changes.packages)

    return OperationResult(
        command=("pin",),
        data=PinData(packages=tuple(changes.packages), skipped=tuple(changes.skipped)),
        messages=tuple(messages),
    )


def _missing_result(command: tuple[str, ...], environment: str) -> OperationResult[PinData]:
    error: Final[str] = f"pipx does not manage package {environment}"
    return OperationResult(
        command=command,
        data=PinData(packages=(), skipped=()),
        messages=(OutputMessage(text=error, stream=OutputStream.STDERR, level=OutputLevel.ERROR),),
        exit_code=ExitCode(1),
        errors=(OperationError(code="package_pin_failed", message=error, environment=environment),),
    )


def _environment_name(metadata: PipxMetadata, main_name: str) -> str:
    name = f"{main_name}{metadata.main_package.exposure.suffix}"
    return name if canonicalize_name(name) == metadata.venv_dir.name else metadata.venv_dir.name


def _pin_requested(metadata: PipxMetadata, environment: str, skip: Sequence[str]) -> _PinChanges:
    changes: Final[_PinChanges] = _PinChanges(packages=[], skipped=[], messages=[])
    skip_names: Final[set[str]] = {canonicalize_name(requested) for requested in skip}
    for package_name, package in metadata.injected_packages.items():
        if package_name == metadata.main_package.package:
            continue
        if (
            canonicalize_name(package_name) in skip_names
            or canonicalize_name(f"{package_name}{package.exposure.suffix}") in skip_names
        ):
            changes.skipped.append(_SkippedPackage(environment=environment, package=package_name, reason="requested"))
            continue
        if package.pinned:
            changes.skipped.append(
                _SkippedPackage(environment=environment, package=package_name, reason="already-pinned")
            )
            changes.messages.append(OutputMessage(text=f"pipx already pins {package_name}; skipping it."))
            continue
        changes.packages.append(_change_pin(metadata, environment, package_name, package, status=_PinStatus.PINNED))
    return changes


class _PinChanges(NamedTuple):
    packages: list[_ChangedPackage]
    skipped: list[_SkippedPackage]
    messages: list[OutputMessage]


@dataclass(frozen=True, slots=True, kw_only=True)
class _SkippedPackage:
    environment: str
    package: str
    reason: str


def _change_pin(
    metadata: PipxMetadata,
    environment: str,
    package_name: str,
    package: PackageInfo,
    *,
    status: _PinStatus,
) -> _ChangedPackage:
    updated: Final[PackageInfo] = replace(package, pinned=status is _PinStatus.PINNED)
    injected: Final[bool] = package_name != metadata.main_package.package
    if injected:
        metadata.injected_packages[package_name] = updated
    else:
        metadata.main_package = updated
    return _ChangedPackage(
        environment=environment,
        package=f"{package.package}{package.exposure.suffix}",
        version=package.package_version,
        status=status,
        injected=injected,
        location=str(metadata.venv_dir),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class _ChangedPackage:
    environment: str
    package: str
    version: str
    status: _PinStatus
    injected: bool
    location: str


def _pin_all(metadata: PipxMetadata, environment: str, main_name: str) -> _PinChanges:
    changes: Final[_PinChanges] = _PinChanges(packages=[], skipped=[], messages=[])
    main_package: Final[PackageInfo] = metadata.main_package
    for package_name, package in (metadata.injected_packages | {main_name: main_package}).items():
        if package.pinned:
            changes.skipped.append(
                _SkippedPackage(environment=environment, package=package_name, reason="already-pinned")
            )
            continue
        changes.packages.append(_change_pin(metadata, environment, package_name, package, status=_PinStatus.PINNED))
    if main_package.pinned:
        changes.messages.append(
            OutputMessage(text=f"pipx already pins package {main_package.package} {SLEEP}", stream=OutputStream.LOG)
        )
    return changes


def _summary_message(environment: str, status: _PinStatus, package_count: int) -> OutputMessage:
    package_label: Final[str] = "package" if package_count == 1 else "packages"
    return OutputMessage(text=BOLD(f"pipx {status.value} {package_count} {package_label} in venv {environment}"))


class _PinStatus(StrEnum):
    PINNED = "pinned"
    UNPINNED = "unpinned"


@dataclass(frozen=True, slots=True, kw_only=True)
class PinData(OperationData):
    """Result data of the pin and unpin commands.

    :ivar packages: the packages whose pin changed.
    :ivar skipped: the packages that were skipped, with the reason.
    """

    packages: tuple[_ChangedPackage, ...]
    skipped: tuple[_SkippedPackage, ...]


def unpin(venv_dir: Path) -> OperationResult[PinData]:
    """Remove the pins of the packages of an environment.

    :param venv_dir: the directory of the environment.
    :returns: the result listing the unpinned packages.
    """
    metadata: Final[PipxMetadata] = PipxMetadata(venv_dir)
    if (main_name := metadata.main_package.package) is None:
        return _missing_result(("unpin",), venv_dir.name)

    environment = _environment_name(metadata, main_name)
    packages: Final[list[_ChangedPackage]] = []
    skipped: Final[list[_SkippedPackage]] = []
    for package_name, package in (metadata.injected_packages | {main_name: metadata.main_package}).items():
        if not package.pinned:
            skipped.append(_SkippedPackage(environment=environment, package=package_name, reason="not-pinned"))
            continue
        packages.append(_change_pin(metadata, environment, package_name, package, status=_PinStatus.UNPINNED))

    if packages:
        metadata.write(raise_on_error=True)

    return OperationResult(
        command=("unpin",),
        data=PinData(packages=tuple(packages), skipped=tuple(skipped)),
        messages=(
            (
                _summary_message(environment, _PinStatus.UNPINNED, len(packages)),
                *(OutputMessage(text=f"  - {package.package}") for package in packages),
            )
            if packages
            else (OutputMessage(text=f"pipx found no pinned packages in venv {environment}", stream=OutputStream.LOG),)
        ),
    )


__all__ = [
    "PinData",
    "pin",
    "unpin",
]
