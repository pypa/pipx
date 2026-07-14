from __future__ import annotations

import logging
import os
from dataclasses import dataclass, replace
from enum import Enum
from typing import TYPE_CHECKING, Final

from pipx import commands, paths
from pipx.colors import bold, red
from pipx.commands.common import expose_package_resources, locked_package_message, validate_expected_apps
from pipx.commands.outdated import inspect_outdated
from pipx.commands.transaction import preserve_venv
from pipx.constants import ExitCode
from pipx.emojis import sleep
from pipx.package_specifier import parse_specifier_for_upgrade
from pipx.result import OperationData, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.shared_libs import shared_libs
from pipx.util import PipxError, pipx_wrap
from pipx.venv import Venv, VenvContainer

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from pathlib import Path

    from filelock import BaseFileLock

    from pipx.commands.outdated import OutdatedData
    from pipx.pipx_metadata_file import PackageInfo

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def upgrade(
    venv_dirs: dict[str, Path],
    python: str | None,
    pip_args: list[str],
    venv_args: list[str],
    verbose: bool,
    *,
    include_injected: bool,
    force: bool,
    install: bool,
    python_flag_passed: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
    cooldown_days: int | None = None,
) -> OperationResult[UpgradeData]:
    results: Final[list[PackageUpgradeResult]] = []

    for venv_dir in venv_dirs.values():
        with VenvContainer(venv_dir.parent).venv_lock(venv_dir) as venv_lock:
            results.extend(
                _upgrade_venv(
                    venv_dir,
                    pip_args,
                    verbose,
                    include_injected=include_injected,
                    force=force,
                    install=install,
                    venv_args=venv_args,
                    python=python,
                    python_flag_passed=python_flag_passed,
                    backend=backend,
                    env_backend=env_backend,
                    venv_lock=venv_lock,
                    cooldown_days=cooldown_days,
                )
            )

    package_results: Final[tuple[PackageUpgradeResult, ...]] = tuple(results)
    return OperationResult(
        command="upgrade",
        data=UpgradeData(packages=package_results, skipped=(), failures=()),
        messages=tuple(
            message for result in package_results for message in _package_messages(result, upgrading_all=False)
        ),
    )


def upgrade_all(
    venv_container: VenvContainer,
    verbose: bool,
    *,
    pip_args: list[str],
    include_injected: bool,
    skip: Sequence[str],
    force: bool,
    python_flag_passed: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
    cooldown_days: int | None = None,
) -> OperationResult[UpgradeData]:
    outdated: Final[OutdatedData] = inspect_outdated(
        venv_container,
        include_injected=include_injected,
        upgradable_only=True,
        pip_args=pip_args,
        skip=skip,
        backend=backend,
        env_backend=env_backend,
    )
    candidates: Final[set[tuple[str, str]]] = {
        (package.environment, package.package) for package in outdated.packages
    } | {
        (package.environment, package.package)
        for package in outdated.skipped
        if package.reason in {"editable", "non-index"}
    }
    check_failures: Final[dict[str, list[str]]] = {}
    for failure in outdated.failures:
        check_failures.setdefault(failure.environment, []).append(failure.error)

    failures: Final[list[FailedUpgrade]] = []
    messages: Final[list[OutputMessage]] = []
    results: Final[list[PackageUpgradeResult]] = []
    skipped: Final[list[SkippedUpgrade]] = []

    for venv_dir in venv_container.iter_venv_dirs():
        if venv_dir.name in skip:
            skipped.append(SkippedUpgrade(venv_dir.name, "requested"))
            continue
        with venv_container.venv_lock(venv_dir) as venv_lock:
            venv: Venv = Venv(venv_dir, verbose=verbose, backend=backend, env_backend=env_backend)
            if "--editable" in venv.pipx_metadata.main_package.pip_args:
                skipped.append(SkippedUpgrade(venv_dir.name, "editable"))
                continue
            try:
                _validate_venv_for_upgrade(venv_dir, venv)
                if venv.pipx_metadata.main_package.lock_file is None and (errors := check_failures.get(venv.name)):
                    raise PipxError("\n".join(errors), wrap_message=False)
                packages_to_upgrade: set[str] = {
                    package_name
                    for package_name, package in venv.package_metadata.items()
                    if (package_name == venv.main_package_name or include_injected)
                    and (venv.name, f"{package_name}{package.suffix}") in candidates
                }
                package_results: tuple[PackageUpgradeResult, ...] = _upgrade_venv(
                    venv_dir,
                    pip_args,
                    verbose=verbose,
                    include_injected=include_injected,
                    force=force,
                    python_flag_passed=python_flag_passed,
                    backend=backend,
                    env_backend=env_backend,
                    venv=venv,
                    packages_to_upgrade=packages_to_upgrade,
                    venv_lock=venv_lock,
                    cooldown_days=cooldown_days,
                )
                results.extend(package_results)
                for result in package_results:
                    messages.extend(_package_messages(result, upgrading_all=True))
            except PipxError as error:
                failures.append(FailedUpgrade(venv_dir.name, str(error)))
                messages.append(OutputMessage(str(error), stream=OutputStream.STDERR, level=OutputLevel.ERROR))
    if not any(result.status is UpgradeStatus.UPGRADED for result in results):
        messages.append(OutputMessage(f"No packages upgraded after running 'pipx upgrade-all' {sleep}"))
    if failures:
        messages.append(
            OutputMessage(
                f"The following package(s) failed to upgrade: {','.join(failure.environment for failure in failures)}",
                stream=OutputStream.STDERR,
                level=OutputLevel.ERROR,
            )
        )
    return OperationResult(
        command="upgrade-all",
        data=UpgradeData(packages=tuple(results), skipped=tuple(skipped), failures=tuple(failures)),
        messages=tuple(messages),
        exit_code=ExitCode(1 if failures else 0),
    )


def upgrade_shared(
    verbose: bool,
    pip_args: list[str],
) -> OperationResult[SharedData]:
    # pip-backed installs use this environment regardless of the installed environments' backends.
    shared_libs.upgrade(verbose=verbose, pip_args=pip_args, raises=True)
    return OperationResult(
        command="upgrade-shared",
        data=SharedData(location=str(shared_libs.root)),
        messages=(OutputMessage(f"Upgraded the shared libraries in {shared_libs.root}."),),
    )


def _upgrade_venv(
    venv_dir: Path,
    pip_args: list[str],
    verbose: bool,
    *,
    include_injected: bool,
    force: bool,
    install: bool = False,
    venv_args: list[str] | None = None,
    python: str | None = None,
    python_flag_passed: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
    venv: Venv | None = None,
    packages_to_upgrade: Collection[str] | None = None,
    venv_lock: BaseFileLock | None = None,
    cooldown_days: int | None = None,
) -> tuple[PackageUpgradeResult, ...]:
    if not venv_dir.is_dir():
        if install:
            commands.install(
                venv_dir=None,
                venv_args=venv_args or [],
                package_names=None,
                package_specs=[str(venv_dir).split(os.path.sep)[-1]],
                local_bin_dir=paths.ctx.bin_dir,
                local_man_dir=paths.ctx.man_dir,
                python=python,
                pip_args=pip_args,
                verbose=verbose,
                force=force,
                reinstall=False,
                include_dependencies=False,
                include_apps_from=(),
                preinstall_packages=None,
                python_flag_passed=python_flag_passed,
                backend=backend,
                env_backend=env_backend,
                venv_lock=venv_lock,
                cooldown_days=cooldown_days,
            )
            return ()
        raise PipxError(
            f"""
            Package is not installed. Expected to find {venv_dir!s}, but it
            does not exist.
            """
        )

    if venv_args and not install:
        _LOGGER.info(f"Ignoring {', '.join(venv_args)} as not combined with --install")

    if python and not install:
        _LOGGER.info("Ignoring --python as not combined with --install")

    if venv is None:
        venv = Venv(venv_dir, verbose=verbose, backend=backend, env_backend=env_backend)
        _validate_venv_for_upgrade(venv_dir, venv)

    main_package: Final[PackageInfo] = venv.pipx_metadata.main_package
    if main_package.lock_file is not None:
        return (
            PackageUpgradeResult(
                environment=venv.name,
                package=venv.name,
                previous_version=main_package.package_version,
                version=main_package.package_version,
                status=UpgradeStatus.LOCKED,
                injected=False,
                location=str(venv.root),
            ),
        )

    main_pip_args: Final[list[str]] = pip_args or main_package.pip_args
    if packages_to_upgrade is None or packages_to_upgrade:
        venv.check_upgrade_shared_libs(pip_args=main_pip_args, verbose=verbose)

    with preserve_venv(
        venv_dir,
        enabled=(packages_to_upgrade is None or bool(packages_to_upgrade))
        and any(package.expected_apps for package in venv.package_metadata.values()),
    ):
        return _upgrade_packages(
            venv,
            main_pip_args,
            pip_args,
            include_injected=include_injected,
            force=force,
            packages_to_upgrade=packages_to_upgrade,
            cooldown_days=cooldown_days,
        )


def _validate_venv_for_upgrade(venv_dir: Path, venv: Venv) -> None:
    if not venv.python_path.is_file():
        raise PipxError(
            f"Not upgrading {red(bold(venv_dir.name))}. It has an invalid python interpreter {venv.python_path}.\n"
            f"This usually happens after a system Python upgrade.\n"
            f"To fix, execute: pipx reinstall-all",
            wrap_message=False,
        )

    if not venv.package_metadata:
        raise PipxError(
            f"Not upgrading {red(bold(venv_dir.name))}. It has missing internal pipx metadata.\n"
            f"It was likely installed using a pipx version before 0.15.0.0.\n"
            f"Please uninstall and install this package to fix.",
            wrap_message=False,
        )


def _upgrade_packages(
    venv: Venv,
    main_pip_args: list[str],
    pip_args: list[str],
    *,
    include_injected: bool,
    force: bool,
    packages_to_upgrade: Collection[str] | None,
    cooldown_days: int | None,
) -> tuple[PackageUpgradeResult, ...]:
    package_names: Final[list[str]] = [venv.main_package_name]
    if include_injected:
        package_names.extend(
            package_name for package_name in venv.package_metadata if package_name != venv.main_package_name
        )

    selected: Final[set[str]] = (
        set(package_names) if packages_to_upgrade is None else set(package_names).intersection(packages_to_upgrade)
    )
    if cooldown_days is not None:
        cooldown_packages: Final[tuple[str, ...]] = tuple(
            package_name
            for package_name in package_names
            if package_name not in selected
            and not venv.package_metadata[package_name].pinned
            and venv.package_metadata[package_name].cooldown_days != cooldown_days
        )
        for package_name in cooldown_packages:
            updated: PackageInfo = replace(venv.package_metadata[package_name], cooldown_days=cooldown_days)
            if package_name == venv.main_package_name:
                venv.pipx_metadata.main_package = updated
            else:
                venv.pipx_metadata.injected_packages[package_name] = updated
        if cooldown_packages:
            venv.pipx_metadata.write()
    if selected:
        venv.upgrade_packaging_libraries(main_pip_args)
    results: Final[list[PackageUpgradeResult]] = []
    for package_name in package_names:
        if package_name in selected:
            results.append(
                _upgrade_package(
                    venv,
                    package_name,
                    main_pip_args
                    if package_name == venv.main_package_name
                    else pip_args or venv.package_metadata[package_name].pip_args,
                    is_main_package=package_name == venv.main_package_name,
                    force=force,
                    cooldown_days=cooldown_days,
                )
            )
        else:
            results.append(
                _package_result(
                    venv,
                    package_name,
                    UpgradeStatus.PINNED if venv.package_metadata[package_name].pinned else UpgradeStatus.UNCHANGED,
                )
            )

    return tuple(results)


def _upgrade_package(
    venv: Venv,
    package_name: str,
    pip_args: list[str],
    is_main_package: bool,
    force: bool,
    cooldown_days: int | None,
) -> PackageUpgradeResult:
    package_metadata = venv.package_metadata[package_name]

    if package_metadata.package_or_url is None:
        raise PipxError(f"Internal Error: package {package_name} has corrupt pipx metadata.")
    if package_metadata.pinned:
        return _package_result(venv, package_name, UpgradeStatus.PINNED)

    old_version: Final[str] = package_metadata.package_version

    venv.upgrade_package(
        package_name,
        parse_specifier_for_upgrade(package_metadata.package_or_url),
        pip_args,
        include_dependencies=package_metadata.include_dependencies,
        include_apps_from=package_metadata.include_apps_from,
        include_apps=package_metadata.include_apps,
        is_main_package=is_main_package,
        suffix=package_metadata.suffix,
        expected_apps=package_metadata.expected_apps,
        cooldown_days=cooldown_days if cooldown_days is not None else package_metadata.cooldown_days,
    )

    package_metadata = venv.package_metadata[package_name]
    validate_expected_apps(venv, package_name, package_metadata.expected_apps)

    new_version: Final[str] = package_metadata.package_version

    if venv.pipx_metadata.exposure_enabled:
        expose_package_resources(package_metadata, paths.ctx.bin_dir, paths.ctx.man_dir, force=force)

    return PackageUpgradeResult(
        environment=venv.name,
        package=f"{package_metadata.package}{package_metadata.suffix}",
        previous_version=old_version,
        version=new_version,
        status=UpgradeStatus.UNCHANGED if old_version == new_version else UpgradeStatus.UPGRADED,
        injected=package_name != venv.main_package_name,
        location=str(venv.root),
    )


def _package_result(venv: Venv, package_name: str, status: UpgradeStatus) -> PackageUpgradeResult:
    package_metadata: Final[PackageInfo] = venv.package_metadata[package_name]
    return PackageUpgradeResult(
        environment=venv.name,
        package=f"{package_metadata.package}{package_metadata.suffix}",
        previous_version=package_metadata.package_version,
        version=package_metadata.package_version,
        status=status,
        injected=package_name != venv.main_package_name,
        location=str(venv.root),
    )


def _package_messages(result: PackageUpgradeResult, *, upgrading_all: bool) -> tuple[OutputMessage, ...]:
    if result.status is UpgradeStatus.LOCKED:
        return (OutputMessage(locked_package_message(result.environment)),)
    if result.status is UpgradeStatus.PINNED:
        subject: Final[str] = (
            f"package {result.package} in venv {result.environment}"
            if result.injected
            else f"package {result.environment}"
        )
        return (
            OutputMessage(
                f"Not upgrading pinned {subject}. Run `pipx unpin {result.environment}` to unpin it.",
                stream=OutputStream.LOG,
            ),
        )
    if result.status is UpgradeStatus.UNCHANGED:
        if upgrading_all:
            return ()
        return (
            OutputMessage(
                pipx_wrap(
                    f"""
                    {result.package} is already at latest version {result.previous_version}
                    (location: {result.location})
                    """
                )
            ),
        )
    return (
        OutputMessage(
            pipx_wrap(
                f"""
                upgraded package {result.package} from {result.previous_version} to
                {result.version} (location: {result.location})
                """
            )
        ),
    )


class UpgradeStatus(str, Enum):
    LOCKED = "locked"
    PINNED = "pinned"
    UNCHANGED = "unchanged"
    UPGRADED = "upgraded"


@dataclass(frozen=True)
class PackageUpgradeResult:
    environment: str
    package: str
    previous_version: str
    version: str
    status: UpgradeStatus
    injected: bool
    location: str


@dataclass(frozen=True)
class SkippedUpgrade:
    environment: str
    reason: str


@dataclass(frozen=True)
class FailedUpgrade:
    environment: str
    error: str


@dataclass(frozen=True)
class UpgradeData(OperationData):
    packages: tuple[PackageUpgradeResult, ...]
    skipped: tuple[SkippedUpgrade, ...]
    failures: tuple[FailedUpgrade, ...]


@dataclass(frozen=True)
class SharedData(OperationData):
    location: str


__all__ = [
    "SharedData",
    "UpgradeData",
    "upgrade",
    "upgrade_all",
    "upgrade_shared",
]
