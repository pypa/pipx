import logging
import os
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final

from pipx import commands, paths
from pipx.colors import bold, red
from pipx.commands.common import expose_resources_globally
from pipx.constants import EXIT_CODE_OK, ExitCode
from pipx.emojis import sleep
from pipx.package_specifier import parse_specifier_for_upgrade
from pipx.result import OperationData, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.shared_libs import shared_libs
from pipx.util import PipxError, pipx_wrap
from pipx.venv import Venv, VenvContainer

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


class UpgradeStatus(str, Enum):
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


def _upgrade_package(
    venv: Venv,
    package_name: str,
    pip_args: list[str],
    is_main_package: bool,
    force: bool,
) -> PackageUpgradeResult:
    package_metadata = venv.package_metadata[package_name]

    if package_metadata.package_or_url is None:
        raise PipxError(f"Internal Error: package {package_name} has corrupt pipx metadata.")
    elif package_metadata.pinned:
        return PackageUpgradeResult(
            environment=venv.name,
            package=f"{package_metadata.package}{package_metadata.suffix}",
            previous_version=package_metadata.package_version,
            version=package_metadata.package_version,
            status=UpgradeStatus.PINNED,
            injected=package_metadata.package != venv.main_package_name,
            location=str(venv.root),
        )

    package_or_url = parse_specifier_for_upgrade(package_metadata.package_or_url)
    old_version = package_metadata.package_version

    venv.upgrade_package(
        package_name,
        package_or_url,
        pip_args,
        include_dependencies=package_metadata.include_dependencies,
        include_apps=package_metadata.include_apps,
        is_main_package=is_main_package,
        suffix=package_metadata.suffix,
    )

    package_metadata = venv.package_metadata[package_name]

    display_name = f"{package_metadata.package}{package_metadata.suffix}"
    new_version = package_metadata.package_version

    if package_metadata.include_apps:
        expose_resources_globally(
            "app",
            paths.ctx.bin_dir,
            package_metadata.app_paths,
            force=force,
            suffix=package_metadata.suffix,
        )
        expose_resources_globally("man", paths.ctx.man_dir, package_metadata.man_paths, force=force)

    if package_metadata.include_dependencies:
        for app_paths in package_metadata.app_paths_of_dependencies.values():
            expose_resources_globally(
                "app",
                paths.ctx.bin_dir,
                app_paths,
                force=force,
                suffix=package_metadata.suffix,
            )
        for man_paths in package_metadata.man_paths_of_dependencies.values():
            expose_resources_globally("man", paths.ctx.man_dir, man_paths, force=force)

    return PackageUpgradeResult(
        environment=venv.name,
        package=display_name,
        previous_version=old_version,
        version=new_version,
        status=UpgradeStatus.UNCHANGED if old_version == new_version else UpgradeStatus.UPGRADED,
        injected=package_name != venv.main_package_name,
        location=str(venv.root),
    )


def _package_messages(result: PackageUpgradeResult, *, upgrading_all: bool) -> tuple[OutputMessage, ...]:
    if result.status is UpgradeStatus.PINNED:
        subject = (
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
    shared_libs_already_checked: bool = False,
) -> tuple[PackageUpgradeResult, ...]:
    """Return package upgrade results.

    ``upgrade-all`` passes ``venv`` and ``shared_libs_already_checked=True``
    after its own pre-checks to avoid re-running them per venv.
    """
    if not venv_dir.is_dir():
        if install:
            if venv_args is None:
                venv_args = []
            commands.install(
                venv_dir=None,
                venv_args=venv_args,
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
                preinstall_packages=None,
                python_flag_passed=python_flag_passed,
                backend=backend,
                env_backend=env_backend,
            )
            return ()
        else:
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
    main_pip_args = pip_args or venv.pipx_metadata.main_package.pip_args
    if not shared_libs_already_checked:
        venv.check_upgrade_shared_libs(pip_args=main_pip_args, verbose=verbose)

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

    venv.upgrade_packaging_libraries(main_pip_args)

    results: list[PackageUpgradeResult] = []

    package_name = venv.main_package_name
    results.append(
        _upgrade_package(
            venv,
            package_name,
            main_pip_args,
            is_main_package=True,
            force=force,
        )
    )

    if include_injected:
        for package_name in venv.package_metadata:
            if package_name == venv.main_package_name:
                continue
            injected_pip_args = pip_args or venv.package_metadata[package_name].pip_args
            results.append(
                _upgrade_package(
                    venv,
                    package_name,
                    injected_pip_args,
                    is_main_package=False,
                    force=force,
                )
            )

    return tuple(results)


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
) -> OperationResult[UpgradeData]:
    results: list[PackageUpgradeResult] = []

    for venv_dir in venv_dirs.values():
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
            )
        )

    package_results = tuple(results)
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
) -> OperationResult[UpgradeData]:
    failures: list[FailedUpgrade] = []
    messages: list[OutputMessage] = []
    results: list[PackageUpgradeResult] = []
    skipped: list[SkippedUpgrade] = []

    for venv_dir in venv_container.iter_venv_dirs():
        # Cheap skip-list check first so we don't pay metadata read +
        # cross-backend warning + shared-libs health check on excluded venvs.
        if venv_dir.name in skip:
            skipped.append(SkippedUpgrade(venv_dir.name, "requested"))
            continue
        venv = Venv(venv_dir, verbose=verbose, backend=backend, env_backend=env_backend)
        if "--editable" in venv.pipx_metadata.main_package.pip_args:
            skipped.append(SkippedUpgrade(venv_dir.name, "editable"))
            continue
        venv.check_upgrade_shared_libs(pip_args=pip_args, verbose=verbose)
        try:
            package_results = _upgrade_venv(
                venv_dir,
                pip_args,
                verbose=verbose,
                include_injected=include_injected,
                force=force,
                python_flag_passed=python_flag_passed,
                backend=backend,
                env_backend=env_backend,
                venv=venv,
                shared_libs_already_checked=True,
            )
            results.extend(package_results)
            for result in package_results:
                messages.extend(_package_messages(result, upgrading_all=True))
        except PipxError as e:
            failures.append(FailedUpgrade(venv_dir.name, str(e)))
            messages.append(OutputMessage(str(e), stream=OutputStream.STDERR, level=OutputLevel.ERROR))
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
) -> ExitCode:
    # Always refreshes: the next pip-backed install needs a fresh shared-libs
    # venv even when all currently-installed venvs are uv-backed.
    shared_libs.upgrade(verbose=verbose, pip_args=pip_args, raises=True)
    return EXIT_CODE_OK


__all__ = [
    "UpgradeData",
    "upgrade",
    "upgrade_all",
    "upgrade_shared",
]
