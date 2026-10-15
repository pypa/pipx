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
    "pipx.package_specifier",
    "pipx.pipx_metadata_file",
    "pipx.script",
    "pipx.shared_libs",
    "pipx.util",
    "pipx.venv",
]

import logging
from dataclasses import dataclass, replace
from enum import StrEnum
from functools import partial
from typing import TYPE_CHECKING, Final

from pipx import paths
from pipx.colors import bold, red
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
from pipx.commands.transaction import is_unfinished, marked_unfinished, preserve_venv
from pipx.constants import ExitCode
from pipx.emojis import sleep
from pipx.fanout import fan_out, locked_in_order
from pipx.interpreter import get_default_python
from pipx.package_specifier import parse_specifier_for_upgrade, valid_pypi_name
from pipx.pipx_metadata_file import PipxMetadata
from pipx.result import OperationData, OperationError, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.script import is_script_spec
from pipx.shared_libs import shared_libs
from pipx.util import PipxError, pipx_wrap, run_subprocess
from pipx.venv import Venv, VenvContainer

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from pathlib import Path

    from filelock import BaseFileLock

    from pipx.commands.outdated import OutdatedData
    from pipx.pipx_metadata_file import PackageInfo

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def upgrade(  # ruff:ignore[too-many-arguments]  # mirrors the CLI's flat upgrade option set across the selected venvs
    venv_dirs: dict[str, Path],
    python: str | None,
    pip_args: list[str],
    venv_args: list[str],
    *,
    verbose: bool,
    include_injected: bool,
    force: bool,
    install: bool,
    python_flag_passed: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
    cooldown_days: int | None = None,
) -> OperationResult[UpgradeData]:
    results: Final[list[PackageUpgradeResult]] = []
    install_messages: Final[list[OutputMessage]] = []

    for package_spec, venv_dir in venv_dirs.items():
        with VenvContainer(venv_dir.parent).venv_lock(venv_dir) as venv_lock:
            results.extend(
                _upgrade_venv(
                    venv_dir,
                    pip_args,
                    verbose=verbose,
                    include_injected=include_injected,
                    force=force,
                    install=install,
                    package_spec=package_spec,
                    venv_args=venv_args,
                    python=python,
                    python_flag_passed=python_flag_passed,
                    backend=backend,
                    env_backend=env_backend,
                    venv_lock=venv_lock,
                    cooldown_days=cooldown_days,
                    extra_messages=install_messages,
                )
            )

    package_results: Final[tuple[PackageUpgradeResult, ...]] = tuple(results)
    return OperationResult(
        command=("upgrade",),
        data=UpgradeData(packages=package_results, skipped=()),
        messages=(
            *install_messages,
            *(message for result in package_results for message in _package_messages(result, upgrading_all=False)),
        ),
    )


def upgrade_all(  # ruff:ignore[too-many-arguments]  # mirrors the CLI's flat upgrade-all option set
    venv_container: VenvContainer,
    *,
    verbose: bool,
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
    venv_dirs: Final[list[Path]] = list(venv_container.iter_venv_dirs())
    with expose_shared_resources_in_order(
        (PipxMetadata(venv_dir) for venv_dir in venv_dirs), paths.ctx.bin_dir, paths.ctx.man_dir
    ):
        venv_upgrades: Final[list[_VenvUpgrade]] = fan_out(
            [
                partial(
                    _upgrade_listed_venv,
                    venv_container,
                    venv_dir,
                    verbose=verbose,
                    pip_args=pip_args,
                    include_injected=include_injected,
                    skip=skip,
                    force=force,
                    python_flag_passed=python_flag_passed,
                    backend=backend,
                    env_backend=env_backend,
                    cooldown_days=cooldown_days,
                    candidates=candidates,
                    check_failures=check_failures,
                )
                for venv_dir in venv_dirs
            ],
            sequential=verbose,
            interrupted=lambda index: _interrupted_upgrade(venv_dirs[index]),
        )
    interrupted: Final[list[str]] = []
    for venv_upgrade in venv_upgrades:
        interrupted.extend(venv_upgrade.interrupted)
        messages.extend(venv_upgrade.messages)
        results.extend(venv_upgrade.results)
        skipped.extend(venv_upgrade.skipped)
        failures.extend(venv_upgrade.failures)
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
    if interrupted:
        messages.append(
            OutputMessage(
                f"Interrupted before upgrading: {','.join(interrupted)}",
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
            OperationError(code="package_upgrade_failed", message=f.error, environment=f.environment) for f in failures
        ),
        succeeded=bool(results or skipped),
    )


def _upgrade_listed_venv(  # ruff:ignore[too-many-arguments]  # forwards the flat upgrade-all context for one venv
    venv_container: VenvContainer,
    venv_dir: Path,
    *,
    verbose: bool,
    pip_args: list[str],
    include_injected: bool,
    skip: Sequence[str],
    force: bool,
    python_flag_passed: bool,
    backend: str | None,
    env_backend: str | None,
    cooldown_days: int | None,
    candidates: set[tuple[str, str]],
    check_failures: dict[str, list[str]],
) -> _VenvUpgrade:
    if venv_dir.name in skip:
        return _VenvUpgrade(skipped=(SkippedUpgrade(venv_dir.name, "requested"),))
    with locked_in_order(venv_container.venv_lock(venv_dir)) as venv_lock:
        messages: Final[list[OutputMessage]] = []
        # the check ran against the half changed environment that the repair replaces
        checked: Final[bool] = not is_unfinished(venv_dir)
        try:
            venv: Final[Venv] = _repaired_venv(
                venv_dir,
                verbose=verbose,
                backend=backend,
                env_backend=env_backend,
                venv_lock=venv_lock,
                messages=messages,
            )
            if "--editable" in venv.pipx_metadata.main_package.pip_args:
                return _VenvUpgrade(messages=tuple(messages), skipped=(SkippedUpgrade(venv_dir.name, "editable"),))
            _validate_venv_for_upgrade(venv_dir, venv)
            _raise_check_failures(venv, check_failures if checked else {})
            package_results: Final[tuple[PackageUpgradeResult, ...]] = _upgrade_venv(
                venv_dir,
                pip_args,
                verbose=verbose,
                include_injected=include_injected,
                force=force,
                python_flag_passed=python_flag_passed,
                backend=backend,
                env_backend=env_backend,
                venv=venv,
                packages_to_upgrade={
                    package_name
                    for package_name, package in venv.package_metadata.items()
                    if (package_name == venv.main_package_name or include_injected)
                    and (venv.name, f"{package_name}{package.suffix}") in candidates
                },
                venv_lock=venv_lock,
                cooldown_days=cooldown_days,
                extra_messages=messages,
            )
        except PipxError as error:
            messages.append(OutputMessage(str(error), stream=OutputStream.STDERR, level=OutputLevel.ERROR))
            return _VenvUpgrade(messages=tuple(messages), failures=(FailedUpgrade(venv_dir.name, str(error)),))
    return _VenvUpgrade(
        messages=(
            *messages,
            *(message for result in package_results for message in _package_messages(result, upgrading_all=True)),
        ),
        results=package_results,
    )


def _interrupted_upgrade(venv_dir: Path) -> _VenvUpgrade:
    if not is_unfinished(venv_dir):
        return _VenvUpgrade(interrupted=(venv_dir.name,))
    error: Final[str] = (
        f"Interrupted while upgrading {venv_dir.name}; the next `pipx upgrade-all`, `pipx upgrade {venv_dir.name}` or "
        f"`pipx reinstall {venv_dir.name}` reinstalls it."
    )
    return _VenvUpgrade(
        messages=(OutputMessage(error, stream=OutputStream.STDERR, level=OutputLevel.ERROR),),
        failures=(FailedUpgrade(venv_dir.name, error),),
    )


def _repaired_venv(  # ruff:ignore[too-many-arguments]  # forwards the reinstall context for one venv
    venv_dir: Path,
    *,
    verbose: bool,
    backend: str | None,
    env_backend: str | None,
    venv_lock: BaseFileLock | None,
    messages: list[OutputMessage],
) -> Venv:
    if is_unfinished(venv_dir):
        _LOGGER.warning("%s was left half changed by an interrupted pipx run; reinstalling it first.", venv_dir.name)
        messages.extend(
            reinstall(
                venv_dir=venv_dir,
                local_bin_dir=paths.ctx.bin_dir,
                local_man_dir=paths.ctx.man_dir,
                python=_base_python(Venv(venv_dir)),
                verbose=verbose,
                backend=backend,
                env_backend=env_backend,
                venv_lock=venv_lock,
            ).messages
        )
    return Venv(venv_dir, verbose=verbose, backend=backend, env_backend=env_backend)


def _base_python(venv: Venv) -> str:
    # rebuild on the Python the environment runs on, which only the interpreter knows on Windows, where the
    # environment's python.exe is a launcher rather than a link
    if venv.python_path.is_file():
        return run_subprocess(
            [venv.python_path, "-c", "import sys; print(sys._base_executable)"], log_stdout=False
        ).stdout.strip()
    return get_default_python()


def _raise_check_failures(venv: Venv, check_failures: dict[str, list[str]]) -> None:
    # index-check failures block an unlocked upgrade; raise so the enclosing handler records the environment
    if venv.pipx_metadata.main_package.lock_file is None and (errors := check_failures.get(venv.name)):
        raise PipxError("\n".join(errors), wrap_message=False)


def upgrade_shared(
    pip_args: list[str],
    *,
    verbose: bool,
) -> OperationResult[SharedData]:
    # pip-backed installs use this environment regardless of the installed environments' backends.
    shared_libs.upgrade(verbose=verbose, pip_args=pip_args, raises=True)
    return OperationResult(
        command=("upgrade-shared",),
        data=SharedData(location=str(shared_libs.root)),
        messages=(OutputMessage(f"Upgraded the shared libraries in {shared_libs.root}."),),
    )


def _upgrade_venv(  # ruff:ignore[too-many-arguments]  # upgrade forwards the full install/upgrade context for one venv
    venv_dir: Path,
    pip_args: list[str],
    *,
    verbose: bool,
    include_injected: bool,
    force: bool,
    install: bool = False,
    package_spec: str | None = None,
    venv_args: list[str] | None = None,
    python: str | None = None,
    python_flag_passed: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
    venv: Venv | None = None,
    packages_to_upgrade: Collection[str] | None = None,
    venv_lock: BaseFileLock | None = None,
    cooldown_days: int | None = None,
    extra_messages: list[OutputMessage],
) -> tuple[PackageUpgradeResult, ...]:
    if not venv_dir.is_dir():
        if install:
            installed = install_package(
                venv_dir=None,
                venv_args=venv_args or [],
                package_names=None,
                # the venv directory only carries the package name; the original argument keeps
                # any version specifier or extras the user asked to install
                package_specs=[package_spec or venv_dir.name],
                local_bin_dir=paths.ctx.bin_dir,
                local_man_dir=paths.ctx.man_dir,
                python=python,
                pip_args=pip_args,
                verbose=verbose,
                force=force,
                reinstall=False,
                include_dependencies=False,
                include_resources_from=(),
                preinstall_packages=None,
                python_flag_passed=python_flag_passed,
                backend=backend,
                env_backend=env_backend,
                venv_lock=venv_lock,
                cooldown_days=cooldown_days,
                emit_output=False,
            )
            # install does not raise when it does not render, so surface a failed result here
            if installed.errors:
                raise PipxError(installed.errors[0].message)
            extra_messages.extend(installed.messages)
            return ()
        msg = f"""
            Package is not installed. Expected to find {venv_dir!s}, but it
            does not exist.
            """
        raise PipxError(msg)

    if venv_args and not install:
        _LOGGER.info("Ignoring %s as not combined with --install", ", ".join(venv_args))

    if python and not install:
        _LOGGER.info("Ignoring --python as not combined with --install")

    if venv is None:
        venv = _repaired_venv(
            venv_dir,
            verbose=verbose,
            backend=backend,
            env_backend=env_backend,
            venv_lock=venv_lock,
            messages=extra_messages,
        )
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
                interpreter=venv.pipx_metadata.python_version,
                backend=venv.pipx_metadata.backend,
            ),
        )

    main_pip_args: Final[list[str]] = pip_args or main_package.pip_args
    if packages_to_upgrade is None or packages_to_upgrade:
        venv.check_upgrade_shared_libs(pip_args=main_pip_args, verbose=verbose)

    with (
        preserve_venv(
            venv_dir,
            enabled=(packages_to_upgrade is None or bool(packages_to_upgrade))
            and any(package.expected_apps for package in venv.package_metadata.values()),
        ),
        marked_unfinished(venv_dir),
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
        msg = (
            f"Not upgrading {red(bold(venv_dir.name))}. It has an invalid python interpreter {venv.python_path}.\n"
            f"This usually happens after a system Python upgrade.\n"
            f"To fix, execute: pipx reinstall-all"
        )
        raise PipxError(
            msg,
            wrap_message=False,
        )

    if not venv.package_metadata:
        msg = (
            f"Not upgrading {red(bold(venv_dir.name))}. It has missing internal pipx metadata.\n"
            f"It was likely installed using a pipx version before 0.15.0.0.\n"
            f"Please uninstall and install this package to fix."
        )
        raise PipxError(
            msg,
            wrap_message=False,
        )


def _upgrade_packages(  # ruff:ignore[too-many-arguments]  # upgrade needs both pip-arg sets plus the injected/force/cooldown flags
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


def _upgrade_package(  # ruff:ignore[too-many-arguments]  # upgrade of one package needs its pip args plus the main/force/cooldown context
    venv: Venv,
    package_name: str,
    pip_args: list[str],
    *,
    is_main_package: bool,
    force: bool,
    cooldown_days: int | None,
) -> PackageUpgradeResult:
    package_metadata = venv.package_metadata[package_name]

    if package_metadata.package_or_url is None:
        msg = f"Internal Error: package {package_name} has corrupt pipx metadata."
        raise PipxError(msg)
    if package_metadata.pinned:
        return _package_result(venv, package_name, UpgradeStatus.PINNED)

    old_version: Final[str] = package_metadata.package_version
    previous_resource_paths: Final[set[Path]] = get_expected_venv_resource_paths(
        venv, paths.ctx.bin_dir, paths.ctx.man_dir
    )

    venv.upgrade_package(
        package_name,
        parse_specifier_for_upgrade(package_metadata.package_or_url),
        pip_args,
        include_dependencies=package_metadata.include_dependencies,
        include_resources_from=package_metadata.include_resources_from,
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
        remove_stale_venv_resources(previous_resource_paths, venv, paths.ctx.bin_dir, paths.ctx.man_dir)

    return PackageUpgradeResult(
        environment=venv.name,
        package=f"{package_metadata.package}{package_metadata.suffix}",
        previous_version=old_version,
        version=new_version,
        status=UpgradeStatus.UNCHANGED if old_version == new_version else UpgradeStatus.UPGRADED,
        injected=package_name != venv.main_package_name,
        location=str(venv.root),
        interpreter=venv.pipx_metadata.python_version,
        backend=venv.pipx_metadata.backend,
        source=_local_source(package_metadata),
    )


def _local_source(package_metadata: PackageInfo) -> str | None:
    """The install source when it is a local path/URL rather than an index name, else None."""
    if package_metadata.package_or_url is not None and valid_pypi_name(package_metadata.package_or_url) is None:
        return package_metadata.package_or_url
    return None


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
        interpreter=venv.pipx_metadata.python_version,
        backend=venv.pipx_metadata.backend,
        source=_local_source(package_metadata),
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
        if result.source is not None:
            remedy: Final[str] = (
                ""
                if result.injected or is_script_spec(result.source)
                else (f" To track index releases, reinstall by package name: pipx install --force {result.environment}")
            )
            return (
                OutputMessage(
                    pipx_wrap(
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


class UpgradeStatus(StrEnum):
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
    interpreter: str | None
    backend: str
    source: str | None = None


@dataclass(frozen=True)
class SkippedUpgrade:
    environment: str
    reason: str


@dataclass(frozen=True)
class FailedUpgrade:
    environment: str
    error: str


@dataclass(frozen=True)
class _VenvUpgrade:
    messages: tuple[OutputMessage, ...] = ()
    results: tuple[PackageUpgradeResult, ...] = ()
    skipped: tuple[SkippedUpgrade, ...] = ()
    failures: tuple[FailedUpgrade, ...] = ()
    interrupted: tuple[str, ...] = ()


@dataclass(frozen=True)
class UpgradeData(OperationData):
    packages: tuple[PackageUpgradeResult, ...]
    skipped: tuple[SkippedUpgrade, ...]


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
