from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from pipx.colors import bold
from pipx.constants import ExitCode
from pipx.emojis import sleep
from pipx.result import OperationData, OperationError, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.venv import Venv

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def pin(
    venv_dir: Path,
    verbose: bool,
    skip: Sequence[str],
    injected_only: bool = False,
) -> OperationResult[PinData]:
    venv = Venv(venv_dir, verbose=verbose)
    if (main_package := venv.package_metadata.get(venv.main_package_name)) is None:
        return _missing_result(("pin",), venv)

    messages: list[OutputMessage] = []
    packages: list[_ChangedPackage] = []
    skipped: list[_SkippedPackage] = []
    if injected_only or skip:
        skip_names = set(skip)
        for package_name in venv.package_metadata:
            if package_name == venv.main_package_name:
                continue
            if package_name in skip_names:
                skipped.append(_SkippedPackage(venv.name, package_name, "requested"))
                continue
            if venv.package_metadata[package_name].pinned:
                skipped.append(_SkippedPackage(venv.name, package_name, "already-pinned"))
                messages.append(OutputMessage(f"pipx already pins {package_name}; skipping it."))
                continue
            _update_pin_info(venv, package_name, is_main_package=False, pinned=True)
            packages.append(_changed_package(venv, package_name, _PinStatus.PINNED))

        if packages:
            messages.append(_summary_message(venv, _PinStatus.PINNED, len(packages)))
            messages.extend(OutputMessage(f"  - {package.package} {package.version}") for package in packages)
    elif main_package.pinned:
        skipped.append(_SkippedPackage(venv.name, str(main_package.package), "already-pinned"))
        messages.append(
            OutputMessage(f"pipx already pins package {main_package.package} {sleep}", stream=OutputStream.LOG)
        )
    else:
        for package_name in venv.package_metadata:
            if venv.package_metadata[package_name].pinned:
                skipped.append(_SkippedPackage(venv.name, package_name, "already-pinned"))
                continue
            _update_pin_info(
                venv,
                package_name,
                is_main_package=package_name == venv.main_package_name,
                pinned=True,
            )
            packages.append(_changed_package(venv, package_name, _PinStatus.PINNED))

    return OperationResult(
        command=("pin",),
        data=PinData(packages=tuple(packages), skipped=tuple(skipped)),
        messages=tuple(messages),
    )


def unpin(venv_dir: Path, verbose: bool) -> OperationResult[PinData]:
    venv = Venv(venv_dir, verbose=verbose)
    if venv.package_metadata.get(venv.main_package_name) is None:
        return _missing_result(("unpin",), venv)

    packages: list[_ChangedPackage] = []
    skipped: list[_SkippedPackage] = []
    for package_name in venv.package_metadata:
        if not venv.package_metadata[package_name].pinned:
            skipped.append(_SkippedPackage(venv.name, package_name, "not-pinned"))
            continue
        _update_pin_info(
            venv,
            package_name,
            is_main_package=package_name == venv.main_package_name,
            pinned=False,
        )
        packages.append(_changed_package(venv, package_name, _PinStatus.UNPINNED))

    if packages:
        messages = [_summary_message(venv, _PinStatus.UNPINNED, len(packages))]
        messages.extend(OutputMessage(f"  - {package.package}") for package in packages)
    else:
        messages = [OutputMessage(f"pipx found no pinned packages in venv {venv.name}", stream=OutputStream.LOG)]

    return OperationResult(
        command=("unpin",),
        data=PinData(packages=tuple(packages), skipped=tuple(skipped)),
        messages=tuple(messages),
    )


def _missing_result(command: tuple[str, ...], venv: Venv) -> OperationResult[PinData]:
    error = f"pipx does not manage package {venv.name}"
    return OperationResult(
        command=command,
        data=PinData(packages=(), skipped=()),
        messages=(OutputMessage(error, stream=OutputStream.STDERR, level=OutputLevel.ERROR),),
        exit_code=ExitCode(1),
        errors=(OperationError(code="package_pin_failed", message=error, environment=venv.name),),
    )


def _update_pin_info(venv: Venv, package_name: str, *, is_main_package: bool, pinned: bool) -> None:
    package = venv.package_metadata[package_name]
    venv.update_package_metadata(
        package_name=str(package.package),
        package_or_url=str(package.package_or_url),
        pip_args=package.pip_args,
        include_dependencies=package.include_dependencies,
        include_resources_from=package.include_resources_from,
        include_apps=package.include_apps,
        is_main_package=is_main_package,
        suffix=package.suffix,
        pinned=pinned,
    )


def _changed_package(venv: Venv, package_name: str, status: _PinStatus) -> _ChangedPackage:
    package = venv.package_metadata[package_name]
    return _ChangedPackage(
        environment=venv.name,
        package=f"{package.package}{package.suffix}",
        version=package.package_version,
        status=status,
        injected=package_name != venv.main_package_name,
        location=str(venv.root),
    )


def _summary_message(venv: Venv, status: _PinStatus, package_count: int) -> OutputMessage:
    package_label = "package" if package_count == 1 else "packages"
    return OutputMessage(bold(f"pipx {status.value} {package_count} {package_label} in venv {venv.name}"))


class _PinStatus(str, Enum):
    PINNED = "pinned"
    UNPINNED = "unpinned"


@dataclass(frozen=True)
class _ChangedPackage:
    environment: str
    package: str
    version: str
    status: _PinStatus
    injected: bool
    location: str


@dataclass(frozen=True)
class _SkippedPackage:
    environment: str
    package: str
    reason: str


@dataclass(frozen=True)
class PinData(OperationData):
    packages: tuple[_ChangedPackage, ...]
    skipped: tuple[_SkippedPackage, ...]


__all__ = [
    "PinData",
    "pin",
    "unpin",
]
