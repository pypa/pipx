from __future__ import annotations

__lazy_modules__ = [
    "functools",
    "pipx",
    "pipx.commands.common",
    "pipx.commands.install",
    "pipx.commands.outdated",
    "pipx.commands.reinstall",
    "pipx.commands.transaction",
    "pipx.fanout",
    "pipx.interpreter",
    "pipx.options",
    "pipx.package_specifier",
    "pipx.pipx_metadata_file",
    "pipx.redact",
    "pipx.script",
    "pipx.shared_libs",
    "pipx.subprocess_runner",
    "pipx.util",
    "pipx.venv",
    "pipx.wrap",
]

import logging
from dataclasses import dataclass, replace
from enum import StrEnum
from functools import partial
from typing import TYPE_CHECKING, Final

from pipx import paths
from pipx.colors import BOLD, RED
from pipx.commands.common import (
    expose_package_resources,
    expose_shared_resources_in_order,
    get_expected_venv_resource_paths,
    locked_package_message,
    remove_stale_venv_resources,
    validate_expected_apps,
)
from pipx.commands.install import install as install_package
from pipx.commands.outdated import inspect_outdated
from pipx.commands.reinstall import reinstall
from pipx.commands.transaction import is_unfinished, marked_unfinished, preserve_venv, runs_from_venv
from pipx.constants import ExitCode
from pipx.emojis import SLEEP
from pipx.fanout import fan_out, locked_in_order
from pipx.interpreter import get_default_python
from pipx.options import CooldownOptions, ExposureOptions, InstallOptions, OutdatedOptions, ReinstallOptions
from pipx.package_specifier import parse_specifier_for_upgrade, trusted_recorded_pip_args, valid_pypi_name
from pipx.pipx_metadata_file import PipxMetadata
from pipx.redact import redact_url_credentials
from pipx.result import OperationData, OperationError, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.script import is_script_spec
from pipx.shared_libs import SHARED_LIBS
from pipx.subprocess_runner import run_subprocess
from pipx.util import PipxError
from pipx.venv import Venv, VenvContainer
from pipx.wrap import pipx_wrap

if TYPE_CHECKING:
    from collections.abc import Collection
    from pathlib import Path

    from filelock import BaseFileLock

    from pipx.commands.outdated import OutdatedData
    from pipx.options import BackendOptions, UpgradeOptions
    from pipx.pipx_metadata_file import PackageInfo

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def upgrade(venv_dirs: dict[str, Path], options: UpgradeOptions) -> OperationResult[UpgradeData]:
    results: Final[list[_PackageUpgradeResult]] = []
    install_messages: Final[list[OutputMessage]] = []

    for package_spec, venv_dir in venv_dirs.items():
        with VenvContainer(venv_dir.parent).venv_lock(venv_dir) as venv_lock:
            results.extend(
                _upgrade_venv(
                    venv_dir, options, package_spec=package_spec, venv_lock=venv_lock, messages=install_messages
                )
            )

    package_results: Final[tuple[_PackageUpgradeResult, ...]] = tuple(results)
    return OperationResult(
        command=("upgrade",),
        data=UpgradeData(packages=package_results, skipped=()),
        messages=(
            *install_messages,
            *(message for result in package_results for message in _package_messages(result, upgrading_all=False)),
        ),
    )


def _upgrade_venv(
    venv_dir: Path,
    options: UpgradeOptions,
    *,
    package_spec: str,
    venv_lock: BaseFileLock,
    messages: list[OutputMessage],
) -> tuple[_PackageUpgradeResult, ...]:
    if not venv_dir.is_dir():
        if options.install:
            installed: Final = install_package(
                None,
                None,
                # the venv directory only carries the package name; the original argument keeps any version specifier
                # or extras the user asked to install
                [package_spec or venv_dir.name],
                InstallOptions(
                    local_bin_dir=paths.CTX.bin_dir,
                    local_man_dir=paths.CTX.man_dir,
                    python=options.python,
                    pip_args=options.pip_args,
                    venv_args=options.venv_args,
                    verbose=options.verbose,
                    force=options.force,
                    reinstall=False,
                    exposure=ExposureOptions(),
                    preinstall_packages=None,
                    python_flag_passed=options.python_flag_passed,
                    backend=options.backend,
                    cooldown=CooldownOptions(cli_days=options.cooldown.days),
                    emit_output=False,
                ),
                venv_lock=venv_lock,
            )
            # install does not raise when it does not render, so surface a failed result here
            if installed.errors:
                raise PipxError(installed.errors[0].message)
            messages.extend(installed.messages)
            return ()
        msg: Final[str] = f"""
            Package is not installed. Expected to find {venv_dir!s}, but it
            does not exist.
            """
        raise PipxError(msg)

    if options.venv_args and not options.install:
        _LOGGER.info("Ignoring %s as not combined with --install", ", ".join(options.venv_args))

    if options.python and not options.install:
        _LOGGER.info("Ignoring --python as not combined with --install")

    venv: Final[Venv] = _repaired_venv(
        venv_dir,
        verbose=options.verbose,
        backend=options.backend,
        venv_lock=venv_lock,
        messages=messages,
    )
    _validate_venv_for_upgrade(venv_dir, venv)
    return _upgrade_venv_packages(venv, options, packages_to_upgrade=None)


def _repaired_venv(
    venv_dir: Path,
    *,
    verbose: bool,
    backend: BackendOptions,
    venv_lock: BaseFileLock | None,
    messages: list[OutputMessage],
) -> Venv:
    if is_unfinished(venv_dir):
        _LOGGER.warning("%s was left half changed by an interrupted pipx run; reinstalling it first.", venv_dir.name)
        messages.extend(
            reinstall(
                venv_dir,
                ReinstallOptions(
                    local_bin_dir=paths.CTX.bin_dir,
                    local_man_dir=paths.CTX.man_dir,
                    python=_base_python(Venv(venv_dir)),
                    verbose=verbose,
                    backend=backend,
                ),
                venv_lock=venv_lock,
            ).messages
        )
    return Venv(venv_dir, verbose=verbose, backend=backend)


def _base_python(venv: Venv) -> str:
    # rebuild on the Python the environment runs on, which only the interpreter knows on Windows, where the
    # environment's python.exe is a launcher rather than a link
    if venv.python_path.is_file():
        return run_subprocess(
            [venv.python_path, "-c", "import sys; print(sys._base_executable)"], log_stdout=False
        ).stdout.strip()
    return get_default_python()


def _validate_venv_for_upgrade(venv_dir: Path, venv: Venv) -> None:
    if not venv.python_path.is_file():
        msg = (
            f"Not upgrading {RED(BOLD(venv_dir.name))}. It has an invalid python interpreter {venv.python_path}.\n"
            f"This usually happens after a system Python upgrade.\n"
            f"To fix, execute: pipx reinstall-all"
        )
        raise PipxError(msg, wrap_message=False)

    if not venv.package_metadata:
        msg = (
            f"Not upgrading {RED(BOLD(venv_dir.name))}. It has no internal pipx metadata.\n"
            "pipx versions before 0.15.0.0 did not record it.\n"
            "Uninstall and install this package to fix it."
        )
        raise PipxError(msg, wrap_message=False)


def _upgrade_venv_packages(
    venv: Venv, options: UpgradeOptions, *, packages_to_upgrade: Collection[str] | None
) -> tuple[_PackageUpgradeResult, ...]:
    main_package: Final[PackageInfo] = venv.pipx_metadata.main_package
    if main_package.lock_file is not None:
        return (
            _PackageUpgradeResult(
                environment=venv.name,
                package=venv.name,
                previous_version=main_package.package_version,
                version=main_package.package_version,
                status=_UpgradeStatus.LOCKED,
                injected=False,
                location=str(venv.root),
                interpreter=venv.pipx_metadata.python_version,
                backend=venv.pipx_metadata.backend,
            ),
        )

    upgrading: Final[bool] = packages_to_upgrade is None or bool(packages_to_upgrade)
    main_pip_args: Final[list[str]] = options.pip_args or (
        trusted_recorded_pip_args(main_package.pip_args, venv.root) if upgrading else main_package.pip_args
    )
    if upgrading:
        venv.check_upgrade_shared_libs(pip_args=main_pip_args, verbose=options.verbose)

    with (
        preserve_venv(
            venv.root,
            enabled=upgrading
            and (runs_from_venv(venv.root) or any(package.expected_apps for package in venv.package_metadata.values())),
        ),
        marked_unfinished(venv.root),
    ):
        return _upgrade_packages(venv, main_pip_args, options, packages_to_upgrade=packages_to_upgrade)


def _upgrade_packages(
    venv: Venv,
    main_pip_args: list[str],
    options: UpgradeOptions,
    *,
    packages_to_upgrade: Collection[str] | None,
) -> tuple[_PackageUpgradeResult, ...]:
    package_names: Final[list[str]] = [venv.main_package_name]
    if options.include_injected:
        package_names.extend(
            package_name for package_name in venv.package_metadata if package_name != venv.main_package_name
        )

    selected: Final[set[str]] = (
        set(package_names) if packages_to_upgrade is None else set(package_names).intersection(packages_to_upgrade)
    )
    # checked before the cooldown write and the first upgrade, so a refused source changes nothing
    selected_pip_args: Final[dict[str, list[str]]] = {
        package_name: main_pip_args
        if package_name == venv.main_package_name
        else options.pip_args or trusted_recorded_pip_args(venv.package_metadata[package_name].pip_args, venv.root)
        for package_name in selected
    }
    cooldown_days: Final[int | None] = options.cooldown.days
    if cooldown_days is not None:
        cooldown_packages: Final[tuple[str, ...]] = tuple(
            package_name
            for package_name in package_names
            if package_name not in selected
            and not venv.package_metadata[package_name].pinned
            and venv.package_metadata[package_name].cooldown_days != cooldown_days
        )
        for package_name in cooldown_packages:
            updated: Final[PackageInfo] = replace(venv.package_metadata[package_name], cooldown_days=cooldown_days)
            if package_name == venv.main_package_name:
                venv.pipx_metadata.main_package = updated
            else:
                venv.pipx_metadata.injected_packages[package_name] = updated
        if cooldown_packages:
            venv.pipx_metadata.write()
    if selected:
        venv.upgrade_packaging_libraries(main_pip_args)
    return tuple(
        _upgrade_package(
            venv,
            package_name,
            selected_pip_args[package_name],
            force=options.force,
            cooldown_days=cooldown_days,
        )
        if package_name in selected
        else _package_result(
            venv,
            package_name,
            _UpgradeStatus.PINNED if venv.package_metadata[package_name].pinned else _UpgradeStatus.UNCHANGED,
        )
        for package_name in package_names
    )


def _upgrade_package(
    venv: Venv,
    package_name: str,
    pip_args: list[str],
    *,
    force: bool,
    cooldown_days: int | None,
) -> _PackageUpgradeResult:
    package_metadata: Final[PackageInfo] = venv.package_metadata[package_name]
    if package_metadata.package_or_url is None:
        msg: Final[str] = f"Internal Error: package {package_name} has corrupt pipx metadata."
        raise PipxError(msg)
    if package_metadata.pinned:
        return _package_result(venv, package_name, _UpgradeStatus.PINNED)

    previous_resource_paths: Final[set[Path]] = get_expected_venv_resource_paths(
        venv, paths.CTX.bin_dir, paths.CTX.man_dir
    )
    venv.upgrade_package(
        package_name,
        parse_specifier_for_upgrade(package_metadata.package_or_url),
        pip_args,
        exposure=ExposureOptions.recorded(package_metadata),
        is_main_package=package_name == venv.main_package_name,
        expected_apps=package_metadata.expected_apps,
        cooldown_days=cooldown_days if cooldown_days is not None else package_metadata.cooldown_days,
    )

    upgraded_metadata: Final[PackageInfo] = venv.package_metadata[package_name]
    validate_expected_apps(venv, package_name, upgraded_metadata.expected_apps)
    if venv.pipx_metadata.exposure_enabled:
        expose_package_resources(upgraded_metadata, paths.CTX.bin_dir, paths.CTX.man_dir, force=force)
        remove_stale_venv_resources(previous_resource_paths, venv, paths.CTX.bin_dir, paths.CTX.man_dir)

    return _PackageUpgradeResult(
        environment=venv.name,
        package=f"{upgraded_metadata.package}{upgraded_metadata.suffix}",
        previous_version=package_metadata.package_version,
        version=upgraded_metadata.package_version,
        status=(
            _UpgradeStatus.UNCHANGED
            if package_metadata.package_version == upgraded_metadata.package_version
            else _UpgradeStatus.UPGRADED
        ),
        injected=package_name != venv.main_package_name,
        location=str(venv.root),
        interpreter=venv.pipx_metadata.python_version,
        backend=venv.pipx_metadata.backend,
        source=_local_source(upgraded_metadata),
    )


def _package_result(venv: Venv, package_name: str, status: _UpgradeStatus) -> _PackageUpgradeResult:
    package_metadata: Final[PackageInfo] = venv.package_metadata[package_name]
    return _PackageUpgradeResult(
        environment=venv.name,
        package=f"{package_metadata.package}{package_metadata.suffix}",
        previous_version=package_metadata.package_version,
        version=package_metadata.package_version,
        status=status,
        injected=package_name != venv.main_package_name,
        location=str(venv.root),
        interpreter=venv.pipx_metadata.python_version,
        backend=venv.pipx_metadata.backend,
        source=_local_source(package_metadata),
    )


def _local_source(package_metadata: PackageInfo) -> str | None:
    if package_metadata.package_or_url is not None and valid_pypi_name(package_metadata.package_or_url) is None:
        return redact_url_credentials(package_metadata.package_or_url)
    return None


def _package_messages(result: _PackageUpgradeResult, *, upgrading_all: bool) -> tuple[OutputMessage, ...]:
    if result.status is _UpgradeStatus.LOCKED:
        return (OutputMessage(text=locked_package_message(result.environment)),)
    if result.status is _UpgradeStatus.PINNED:
        subject: Final[str] = (
            f"package {result.package} in venv {result.environment}"
            if result.injected
            else f"package {result.environment}"
        )
        return (
            OutputMessage(
                text=f"Not upgrading pinned {subject}. Run `pipx unpin {result.environment}` to unpin it.",
                stream=OutputStream.LOG,
            ),
        )
    if result.status is _UpgradeStatus.UNCHANGED:
        if upgrading_all:
            return ()
        if result.source is not None:
            remedy: Final[str] = (
                ""
                if result.injected or is_script_spec(result.source)
                else f" To track index releases, reinstall by package name: pipx install --force {result.environment}"
            )
            return (
                OutputMessage(
                    text=pipx_wrap(
                        f"""
                        {result.package} is unchanged at version {result.previous_version}
                        because it is installed from the local source {result.source};
                        no package index was checked.{remedy}
                        """
                    )
                ),
            )
        return (
            OutputMessage(
                text=pipx_wrap(
                    f"""
                    {result.package} is already at latest version {result.previous_version}
                    (location: {result.location})
                    """
                )
            ),
        )
    return (
        OutputMessage(
            text=pipx_wrap(
                f"""
                upgraded package {result.package} from {result.previous_version} to
                {result.version} (location: {result.location})
                """
            )
        ),
    )


def upgrade_all(venv_container: VenvContainer, options: UpgradeOptions) -> OperationResult[UpgradeData]:
    outdated: Final[OutdatedData] = inspect_outdated(
        venv_container,
        OutdatedOptions(
            include_injected=options.include_injected,
            upgradable_only=True,
            pip_args=options.pip_args,
            skip=options.skip,
            backend=options.backend,
        ),
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

    venv_dirs: Final[list[Path]] = list(venv_container.iter_venv_dirs())
    with expose_shared_resources_in_order(
        (PipxMetadata(venv_dir) for venv_dir in venv_dirs), paths.CTX.bin_dir, paths.CTX.man_dir
    ):
        venv_upgrades: Final[list[_VenvUpgrade]] = fan_out(
            [
                partial(
                    _upgrade_listed_venv,
                    venv_container,
                    venv_dir,
                    options,
                    candidates=candidates,
                    check_failures=check_failures,
                )
                for venv_dir in venv_dirs
            ],
            sequential=options.verbose,
            interrupted=lambda index: _interrupted_upgrade(venv_dirs[index]),
        )
    failures: Final[list[_FailedUpgrade]] = []
    interrupted: Final[list[str]] = []
    messages: Final[list[OutputMessage]] = []
    results: Final[list[_PackageUpgradeResult]] = []
    skipped: Final[list[_SkippedUpgrade]] = []
    for venv_upgrade in venv_upgrades:
        interrupted.extend(venv_upgrade.interrupted)
        messages.extend(venv_upgrade.messages)
        results.extend(venv_upgrade.results)
        skipped.extend(venv_upgrade.skipped)
        failures.extend(venv_upgrade.failures)
    if not any(result.status is _UpgradeStatus.UPGRADED for result in results):
        messages.append(OutputMessage(text=f"No packages upgraded after running 'pipx upgrade-all' {SLEEP}"))
    if failures:
        failed: Final[str] = ",".join(failure.environment for failure in failures)
        messages.append(
            OutputMessage(
                text=f"The following package(s) failed to upgrade: {failed}",
                stream=OutputStream.STDERR,
                level=OutputLevel.ERROR,
            )
        )
    if interrupted:
        messages.append(
            OutputMessage(
                text=f"Interrupted before upgrading: {','.join(interrupted)}",
                stream=OutputStream.STDERR,
                level=OutputLevel.ERROR,
            )
        )
    return OperationResult(
        command=("upgrade-all",),
        data=UpgradeData(packages=tuple(results), skipped=tuple(skipped)),
        messages=tuple(messages),
        exit_code=ExitCode(1 if failures or interrupted else 0),
        errors=tuple(
            OperationError(code="package_upgrade_failed", message=failure.error, environment=failure.environment)
            for failure in failures
        ),
        succeeded=bool(results or skipped),
    )


def _upgrade_listed_venv(
    venv_container: VenvContainer,
    venv_dir: Path,
    options: UpgradeOptions,
    *,
    candidates: set[tuple[str, str]],
    check_failures: dict[str, list[str]],
) -> _VenvUpgrade:
    if venv_dir.name in options.skip:
        return _VenvUpgrade(skipped=(_SkippedUpgrade(environment=venv_dir.name, reason="requested"),))
    with locked_in_order(venv_container.venv_lock(venv_dir)) as venv_lock:
        messages: Final[list[OutputMessage]] = []
        # the check ran against the half changed environment that the repair replaces
        checked: Final[bool] = not is_unfinished(venv_dir)
        try:
            venv: Final[Venv] = _repaired_venv(
                venv_dir,
                verbose=options.verbose,
                backend=options.backend,
                venv_lock=venv_lock,
                messages=messages,
            )
            if "--editable" in venv.pipx_metadata.main_package.pip_args:
                return _VenvUpgrade(
                    messages=tuple(messages),
                    skipped=(_SkippedUpgrade(environment=venv_dir.name, reason="editable"),),
                )
            _validate_venv_for_upgrade(venv_dir, venv)
            _raise_check_failures(venv, check_failures if checked else {})
            package_results: Final[tuple[_PackageUpgradeResult, ...]] = _upgrade_venv_packages(
                venv,
                options,
                packages_to_upgrade={
                    package_name
                    for package_name, package in venv.package_metadata.items()
                    if (package_name == venv.main_package_name or options.include_injected)
                    and (venv.name, f"{package_name}{package.suffix}") in candidates
                },
            )
        except PipxError as error:
            messages.append(OutputMessage(text=str(error), stream=OutputStream.STDERR, level=OutputLevel.ERROR))
            return _VenvUpgrade(
                messages=tuple(messages),
                failures=(_FailedUpgrade(environment=venv_dir.name, error=str(error)),),
            )
    return _VenvUpgrade(
        messages=(
            *messages,
            *(message for result in package_results for message in _package_messages(result, upgrading_all=True)),
        ),
        results=package_results,
    )


def _raise_check_failures(venv: Venv, check_failures: dict[str, list[str]]) -> None:
    # index-check failures block an unlocked upgrade; raise so the enclosing handler records the environment
    if venv.pipx_metadata.main_package.lock_file is None and (errors := check_failures.get(venv.name)):
        raise PipxError("\n".join(errors), wrap_message=False)


def _interrupted_upgrade(venv_dir: Path) -> _VenvUpgrade:
    if not is_unfinished(venv_dir):
        return _VenvUpgrade(interrupted=(venv_dir.name,))
    error: Final[str] = (
        f"Interrupted while upgrading {venv_dir.name}; the next `pipx upgrade-all`, `pipx upgrade {venv_dir.name}` or "
        f"`pipx reinstall {venv_dir.name}` reinstalls it."
    )
    return _VenvUpgrade(
        messages=(OutputMessage(text=error, stream=OutputStream.STDERR, level=OutputLevel.ERROR),),
        failures=(_FailedUpgrade(environment=venv_dir.name, error=error),),
    )


def upgrade_shared(pip_args: list[str], *, verbose: bool) -> OperationResult[SharedData]:
    # pip-backed installs use this environment regardless of the installed environments' backends
    SHARED_LIBS.upgrade(verbose=verbose, pip_args=pip_args, raises=True)
    return OperationResult(
        command=("upgrade-shared",),
        data=SharedData(location=str(SHARED_LIBS.root)),
        messages=(OutputMessage(text=f"Upgraded the shared libraries in {SHARED_LIBS.root}."),),
    )


class _UpgradeStatus(StrEnum):
    LOCKED = "locked"
    PINNED = "pinned"
    UNCHANGED = "unchanged"
    UPGRADED = "upgraded"


@dataclass(frozen=True, slots=True, kw_only=True)
class _PackageUpgradeResult:
    environment: str
    package: str
    previous_version: str
    version: str
    status: _UpgradeStatus
    injected: bool
    location: str
    interpreter: str | None
    backend: str
    source: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class _SkippedUpgrade:
    environment: str
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _FailedUpgrade:
    environment: str
    error: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _VenvUpgrade:
    messages: tuple[OutputMessage, ...] = ()
    results: tuple[_PackageUpgradeResult, ...] = ()
    skipped: tuple[_SkippedUpgrade, ...] = ()
    failures: tuple[_FailedUpgrade, ...] = ()
    interrupted: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class UpgradeData(OperationData):
    packages: tuple[_PackageUpgradeResult, ...]
    skipped: tuple[_SkippedUpgrade, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class SharedData(OperationData):
    location: str


__all__ = [
    "SharedData",
    "UpgradeData",
    "upgrade",
    "upgrade_all",
    "upgrade_shared",
]
