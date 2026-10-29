from __future__ import annotations

__lazy_modules__ = ["packaging.utils", "pipx.options", "pipx.venv"]

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from packaging.utils import canonicalize_name

from pipx.colors import BOLD
from pipx.constants import ExitCode
from pipx.emojis import SLEEP
from pipx.options import ExposureOptions
from pipx.result import OperationData, OperationError, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.venv import Venv

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from pipx.pipx_metadata_file import PackageInfo


def pin(
    venv_dir: Path,
    skip: Sequence[str],
    *,
    verbose: bool,
    injected_only: bool,
) -> OperationResult[PinData]:
    venv: Final[Venv] = Venv(venv_dir, verbose=verbose)
    if (main_package := venv.package_metadata.get(venv.main_package_name)) is None:
        return _missing_result(("pin",), venv)

    messages: Final[list[OutputMessage]] = []
    packages: Final[list[_ChangedPackage]] = []
    skipped: Final[list[_SkippedPackage]] = []
    if injected_only or skip:
        skip_names: Final[set[str]] = {canonicalize_name(requested) for requested in skip}
        for package_name, package in venv.package_metadata.items():
            if package_name == venv.main_package_name:
                continue
            if package_name in skip_names or canonicalize_name(f"{package_name}{package.suffix}") in skip_names:
                skipped.append(_SkippedPackage(environment=venv.name, package=package_name, reason="requested"))
                continue
            if package.pinned:
                skipped.append(_SkippedPackage(environment=venv.name, package=package_name, reason="already-pinned"))
                messages.append(OutputMessage(text=f"pipx already pins {package_name}; skipping it."))
                continue
            _update_pin_info(venv, package_name, is_main_package=False, pinned=True)
            packages.append(_changed_package(venv, package_name, _PinStatus.PINNED))

        if packages:
            messages.append(_summary_message(venv, _PinStatus.PINNED, len(packages)))
            messages.extend(OutputMessage(text=f"  - {package.package} {package.version}") for package in packages)
    else:
        for package_name, package in venv.package_metadata.items():
            if package.pinned:
                skipped.append(_SkippedPackage(environment=venv.name, package=package_name, reason="already-pinned"))
                continue
            _update_pin_info(
                venv,
                package_name,
                is_main_package=package_name == venv.main_package_name,
                pinned=True,
            )
            packages.append(_changed_package(venv, package_name, _PinStatus.PINNED))
        if main_package.pinned:
            messages.append(
                OutputMessage(text=f"pipx already pins package {main_package.package} {SLEEP}", stream=OutputStream.LOG)
            )

    return OperationResult(
        command=("pin",),
        data=PinData(packages=tuple(packages), skipped=tuple(skipped)),
        messages=tuple(messages),
    )


def unpin(venv_dir: Path, *, verbose: bool) -> OperationResult[PinData]:
    venv: Final[Venv] = Venv(venv_dir, verbose=verbose)
    if venv.package_metadata.get(venv.main_package_name) is None:
        return _missing_result(("unpin",), venv)

    packages: Final[list[_ChangedPackage]] = []
    skipped: Final[list[_SkippedPackage]] = []
    for package_name, package in venv.package_metadata.items():
        if not package.pinned:
            skipped.append(_SkippedPackage(environment=venv.name, package=package_name, reason="not-pinned"))
            continue
        _update_pin_info(
            venv,
            package_name,
            is_main_package=package_name == venv.main_package_name,
            pinned=False,
        )
        packages.append(_changed_package(venv, package_name, _PinStatus.UNPINNED))

    return OperationResult(
        command=("unpin",),
        data=PinData(packages=tuple(packages), skipped=tuple(skipped)),
        messages=(
            (
                _summary_message(venv, _PinStatus.UNPINNED, len(packages)),
                *(OutputMessage(text=f"  - {package.package}") for package in packages),
            )
            if packages
            else (OutputMessage(text=f"pipx found no pinned packages in venv {venv.name}", stream=OutputStream.LOG),)
        ),
    )


def _missing_result(command: tuple[str, ...], venv: Venv) -> OperationResult[PinData]:
    error: Final[str] = f"pipx does not manage package {venv.name}"
    return OperationResult(
        command=command,
        data=PinData(packages=(), skipped=()),
        messages=(OutputMessage(text=error, stream=OutputStream.STDERR, level=OutputLevel.ERROR),),
        exit_code=ExitCode(1),
        errors=(OperationError(code="package_pin_failed", message=error, environment=venv.name),),
    )


def _update_pin_info(venv: Venv, package_name: str, *, is_main_package: bool, pinned: bool) -> None:
    package: Final[PackageInfo] = venv.package_metadata[package_name]
    venv.update_package_metadata(
        package_name=str(package.package),
        package_or_url=str(package.package_or_url),
        pip_args=package.pip_args,
        exposure=ExposureOptions.recorded(package),
        is_main_package=is_main_package,
        pinned=pinned,
    )


def _changed_package(venv: Venv, package_name: str, status: _PinStatus) -> _ChangedPackage:
    package: Final[PackageInfo] = venv.package_metadata[package_name]
    return _ChangedPackage(
        environment=venv.name,
        package=f"{package.package}{package.suffix}",
        version=package.package_version,
        status=status,
        injected=package_name != venv.main_package_name,
        location=str(venv.root),
    )


def _summary_message(venv: Venv, status: _PinStatus, package_count: int) -> OutputMessage:
    package_label: Final[str] = "package" if package_count == 1 else "packages"
    return OutputMessage(text=BOLD(f"pipx {status.value} {package_count} {package_label} in venv {venv.name}"))


class _PinStatus(StrEnum):
    PINNED = "pinned"
    UNPINNED = "unpinned"


@dataclass(frozen=True, slots=True, kw_only=True)
class _ChangedPackage:
    environment: str
    package: str
    version: str
    status: _PinStatus
    injected: bool
    location: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _SkippedPackage:
    environment: str
    package: str
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PinData(OperationData):
    packages: tuple[_ChangedPackage, ...]
    skipped: tuple[_SkippedPackage, ...]


__all__ = [
    "PinData",
    "pin",
    "unpin",
]
