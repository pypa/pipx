from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Final

from packaging.utils import canonicalize_name

from pipx.constants import ExitCode
from pipx.package_specifier import extract_index_options, valid_pypi_name
from pipx.result import OperationData, OperationError, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.util import PipxError
from pipx.venv import Venv, VenvContainer

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Sequence
    from pathlib import Path

    from pipx.pipx_metadata_file import PackageInfo

_MAX_OUTDATED_WORKERS: Final[int] = 8


def list_outdated(
    venv_container: VenvContainer,
    venv_dirs: Collection[Path],
    *,
    include_injected: bool,
) -> OperationResult[OutdatedData]:
    data: Final[OutdatedData] = inspect_outdated(
        venv_container,
        include_injected=include_injected,
        venv_dirs=venv_dirs,
    )
    messages: Final[list[OutputMessage]] = [
        OutputMessage(
            f"{failure.environment}: {failure.error}",
            stream=OutputStream.STDERR,
            level=OutputLevel.ERROR,
        )
        for failure in data.failures
    ]
    messages.extend(_package_message(package) for package in data.packages)
    if not data.packages and not data.failures:
        messages.append(
            OutputMessage(
                "pipx found no available upgrades."
                if data.packages_checked
                else "pipx found no index packages to check."
            )
        )
    return OperationResult(
        command=("list",),
        data=data,
        messages=tuple(messages),
        exit_code=ExitCode(1 if data.failures else 0),
        errors=tuple(
            OperationError(
                code="environment_outdated_check_failed", message=failure.error, environment=failure.environment
            )
            for failure in data.failures
        ),
        succeeded=bool(data.packages),
    )


def inspect_outdated(  # ruff:ignore[too-many-arguments]  # forwards the full outdated-check context down the parallel fan-out
    venv_container: VenvContainer,
    *,
    include_injected: bool,
    upgradable_only: bool = False,
    pip_args: Sequence[str] = (),
    skip: Collection[str] = (),
    backend: str | None = None,
    env_backend: str | None = None,
    venv_dirs: Collection[Path] | None = None,
) -> OutdatedData:
    selected_venv_dirs: Final[tuple[Path, ...]] = tuple(
        sorted(
            venv_dir
            for venv_dir in (venv_container.iter_venv_dirs() if venv_dirs is None else venv_dirs)
            if venv_dir.name not in skip
        )
    )
    checks: Final[tuple[_EnvironmentOutdated, ...]] = _list_environments_outdated(
        venv_container,
        selected_venv_dirs,
        include_injected=include_injected,
        upgradable_only=upgradable_only,
        pip_args=pip_args,
        backend=backend,
        env_backend=env_backend,
    )
    packages: Final[tuple[_OutdatedPackage, ...]] = tuple(
        sorted(
            (package for check in checks for package in check.packages),
            key=lambda package: (package.environment, package.package),
        )
    )
    failures: Final[tuple[_FailedEnvironment, ...]] = tuple(
        sorted(
            (failure for check in checks for failure in check.failures),
            key=lambda failure: (failure.environment, failure.error),
        )
    )
    skipped: Final[tuple[_SkippedPackage, ...]] = tuple(
        sorted(
            (package for check in checks for package in check.skipped),
            key=lambda package: (package.environment, package.package),
        )
    )
    return OutdatedData(
        packages_checked=sum(check.packages_checked for check in checks),
        packages=packages,
        skipped=skipped,
        failures=failures,
    )


def _list_environments_outdated(  # ruff:ignore[too-many-arguments]  # forwards the shared outdated-check context to each worker
    venv_container: VenvContainer,
    venv_dirs: tuple[Path, ...],
    *,
    include_injected: bool,
    upgradable_only: bool,
    pip_args: Sequence[str],
    backend: str | None,
    env_backend: str | None,
) -> tuple[_EnvironmentOutdated, ...]:
    if not venv_dirs:
        return ()
    check: Final[Callable[[Path], _EnvironmentOutdated]] = partial(
        _list_environment_outdated,
        venv_container,
        include_injected=include_injected,
        upgradable_only=upgradable_only,
        pip_args=pip_args,
        backend=backend,
        env_backend=env_backend,
    )
    if len(venv_dirs) == 1:
        return (check(venv_dirs[0]),)
    with ThreadPoolExecutor(max_workers=min(_MAX_OUTDATED_WORKERS, len(venv_dirs))) as executor:
        return tuple(executor.map(check, venv_dirs))


def _list_environment_outdated(  # ruff:ignore[too-many-arguments]  # forwards the shared outdated-check context for one venv
    venv_container: VenvContainer,
    venv_dir: Path,
    *,
    include_injected: bool,
    upgradable_only: bool,
    pip_args: Sequence[str],
    backend: str | None,
    env_backend: str | None,
) -> _EnvironmentOutdated:
    with venv_container.venv_lock(venv_dir):
        if not venv_dir.is_dir():
            return _EnvironmentOutdated()
        return _list_venv_outdated(
            Venv(venv_dir, backend=backend, env_backend=env_backend),
            include_injected=include_injected,
            upgradable_only=upgradable_only,
            pip_args=pip_args,
        )


def _list_venv_outdated(
    venv: Venv,
    *,
    include_injected: bool,
    upgradable_only: bool,
    pip_args: Sequence[str],
) -> _EnvironmentOutdated:
    if not venv.package_metadata:
        return _EnvironmentOutdated(failures=(_FailedEnvironment(venv.name, "Missing internal pipx metadata."),))
    if upgradable_only and venv.pipx_metadata.main_package.lock_file is not None:
        return _EnvironmentOutdated()

    failures: Final[list[_FailedEnvironment]] = []
    packages: Final[list[_OutdatedPackage]] = []
    packages_by_index: Final[dict[tuple[str, ...], dict[str, PackageInfo]]] = {}
    skipped: Final[list[_SkippedPackage]] = []
    for package_name, package_info in venv.package_metadata.items():
        if package_name != venv.main_package_name and not include_injected:
            continue
        display_name: str = f"{package_name}{package_info.suffix}"
        if package_info.package_or_url is None:
            failures.append(_FailedEnvironment(venv.name, f"Package {display_name} has corrupt pipx metadata."))
        elif upgradable_only and package_info.pinned:
            continue
        elif "--editable" in package_info.pip_args:
            skipped.append(_SkippedPackage(venv.name, display_name, "editable"))
        elif valid_pypi_name(package_info.package_or_url) is None:
            skipped.append(_SkippedPackage(venv.name, display_name, "non-index"))
        else:
            packages_by_index.setdefault(tuple(extract_index_options(list(pip_args) or package_info.pip_args)), {})[
                canonicalize_name(package_name)
            ] = package_info

    for index_args, package_infos in packages_by_index.items():
        index_packages, index_failures = _collect_outdated(venv, index_args, package_infos)
        packages.extend(index_packages)
        failures.extend(index_failures)
    return _EnvironmentOutdated(
        sum(len(package_infos) for package_infos in packages_by_index.values()),
        tuple(packages),
        tuple(skipped),
        tuple(failures),
    )


def _collect_outdated(
    venv: Venv,
    index_args: tuple[str, ...],
    package_infos: dict[str, PackageInfo],
) -> tuple[list[_OutdatedPackage], list[_FailedEnvironment]]:
    try:
        outdated = list(venv.list_outdated_packages(list(index_args)))
    except PipxError as error:
        return [], [_FailedEnvironment(venv.name, str(error))]
    packages = [
        _OutdatedPackage(
            environment=venv.name,
            package=f"{managed_package.package}{managed_package.suffix}",
            version=package.version,
            latest_version=package.latest_version,
            injected=managed_package.package != venv.main_package_name,
            pinned=managed_package.pinned,
        )
        for package in outdated
        if (managed_package := package_infos.get(canonicalize_name(package.name))) is not None
    ]
    return packages, []


def _package_message(package: _OutdatedPackage) -> OutputMessage:
    subject: Final[str] = (
        f"{package.package} (injected in {package.environment})" if package.injected else package.package
    )
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
class _EnvironmentOutdated:
    packages_checked: int = 0
    packages: tuple[_OutdatedPackage, ...] = ()
    skipped: tuple[_SkippedPackage, ...] = ()
    failures: tuple[_FailedEnvironment, ...] = ()


@dataclass(frozen=True)
class OutdatedData(OperationData):
    def to_dict(self) -> dict[str, object]:
        # failures are surfaced as top-level envelope errors; upgrade still reads this field internally
        data = super().to_dict()
        data.pop("failures", None)
        return data

    packages_checked: int
    packages: tuple[_OutdatedPackage, ...]
    skipped: tuple[_SkippedPackage, ...]
    failures: tuple[_FailedEnvironment, ...]


__all__ = [
    "OutdatedData",
    "inspect_outdated",
    "list_outdated",
]
