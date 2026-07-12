from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from packaging.utils import canonicalize_name

from pipx.constants import ExitCode
from pipx.package_specifier import extract_index_options, valid_pypi_name
from pipx.result import OperationData, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.util import PipxError
from pipx.venv import Venv, VenvContainer

if TYPE_CHECKING:
    from pipx.pipx_metadata_file import PackageInfo


def list_outdated(venv_container: VenvContainer, *, include_injected: bool) -> OperationResult[OutdatedData]:
    packages_checked = 0
    failures: list[_FailedEnvironment] = []
    messages: list[OutputMessage] = []
    outdated_packages: list[_OutdatedPackage] = []
    skipped: list[_SkippedPackage] = []
    for venv_dir in venv_container.iter_locked_venv_dirs(venv_container.iter_venv_dirs()):
        venv = Venv(venv_dir)
        if not venv.package_metadata:
            error = "Missing internal pipx metadata."
            failures.append(_FailedEnvironment(venv.name, error))
            messages.append(OutputMessage(f"{venv.name}: {error}", stream=OutputStream.STDERR, level=OutputLevel.ERROR))
            continue
        packages_by_index: dict[tuple[str, ...], dict[str, PackageInfo]] = {}
        for package_name, package_info in venv.package_metadata.items():
            if package_name != venv.main_package_name and not include_injected:
                continue
            display_name = f"{package_name}{package_info.suffix}"
            if package_info.package_or_url is None:
                error = f"Package {display_name} has corrupt pipx metadata."
                failures.append(_FailedEnvironment(venv.name, error))
                messages.append(
                    OutputMessage(f"{venv.name}: {error}", stream=OutputStream.STDERR, level=OutputLevel.ERROR)
                )
                continue
            if "--editable" in package_info.pip_args:
                skipped.append(_SkippedPackage(venv.name, display_name, "editable"))
                continue
            if valid_pypi_name(package_info.package_or_url) is None:
                skipped.append(_SkippedPackage(venv.name, display_name, "non-index"))
                continue
            packages_by_index.setdefault(tuple(extract_index_options(package_info.pip_args)), {})[
                canonicalize_name(package_name)
            ] = package_info

        for index_args, package_infos in packages_by_index.items():
            packages_checked += len(package_infos)
            try:
                for package in venv.list_outdated_packages(list(index_args)):
                    if (managed_package := package_infos.get(canonicalize_name(package.name))) is None:
                        continue
                    outdated_packages.append(
                        _OutdatedPackage(
                            environment=venv.name,
                            package=f"{managed_package.package}{managed_package.suffix}",
                            version=package.version,
                            latest_version=package.latest_version,
                            injected=managed_package.package != venv.main_package_name,
                            pinned=managed_package.pinned,
                        )
                    )
            except PipxError as error:
                failures.append(_FailedEnvironment(venv.name, str(error)))
                messages.append(
                    OutputMessage(f"{venv.name}: {error}", stream=OutputStream.STDERR, level=OutputLevel.ERROR)
                )

    packages = tuple(sorted(outdated_packages, key=lambda package: (package.environment, package.package)))
    messages.extend(_package_message(package) for package in packages)
    if not packages and not failures:
        messages.append(
            OutputMessage(
                "pipx found no available upgrades." if packages_checked else "pipx found no index packages to check."
            )
        )
    return OperationResult(
        command="list",
        data=OutdatedData(
            packages_checked=packages_checked,
            packages=packages,
            skipped=tuple(sorted(skipped, key=lambda package: (package.environment, package.package))),
            failures=tuple(sorted(failures, key=lambda failure: (failure.environment, failure.error))),
        ),
        messages=tuple(messages),
        exit_code=ExitCode(1 if failures else 0),
    )


def _package_message(package: _OutdatedPackage) -> OutputMessage:
    subject = f"{package.package} (injected in {package.environment})" if package.injected else package.package
    return OutputMessage(
        f"{subject}{' [pinned]' if package.pinned else ''}: {package.version} -> {package.latest_version}"
    )


@dataclass(frozen=True)
class _OutdatedPackage:
    environment: str
    package: str
    version: str
    latest_version: str
    injected: bool
    pinned: bool


@dataclass(frozen=True)
class _SkippedPackage:
    environment: str
    package: str
    reason: str


@dataclass(frozen=True)
class _FailedEnvironment:
    environment: str
    error: str


@dataclass(frozen=True)
class OutdatedData(OperationData):
    packages_checked: int
    packages: tuple[_OutdatedPackage, ...]
    skipped: tuple[_SkippedPackage, ...]
    failures: tuple[_FailedEnvironment, ...]


__all__ = [
    "OutdatedData",
    "list_outdated",
]
