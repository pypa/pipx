from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from tempfile import mkdtemp
from typing import TYPE_CHECKING, Final

from packaging.utils import canonicalize_name

from pipx import paths
from pipx.commands.common import add_suffix
from pipx.commands.inject import inject_dep
from pipx.commands.install import install
from pipx.commands.uninstall import _get_venv_package_infos, _get_venv_resource_paths
from pipx.constants import (
    EXIT_CODE_OK,
    EXIT_CODE_REINSTALL_INVALID_PYTHON,
    EXIT_CODE_REINSTALL_VENV_NONEXISTENT,
    MAN_SECTIONS,
    ExitCode,
)
from pipx.emojis import error, sleep, stars
from pipx.result import OperationData, OperationError, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.util import PipxError, rmdir, safe_unlink
from pipx.venv import Venv, VenvContainer

if TYPE_CHECKING:
    from collections.abc import Sequence

    from filelock import BaseFileLock

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def _create_reinstall_backup(venv_dir: Path) -> Path:
    # keep the backup in the trash rather than beside the venv, so it is not enumerated as a broken environment; the
    # trash shares the home's filesystem, so moving the venv there and back stays an atomic rename
    paths.ctx.trash.mkdir(parents=True, exist_ok=True)
    backup_dir = Path(mkdtemp(prefix=f"{venv_dir.name}-", suffix="-pipx-reinstall", dir=paths.ctx.trash))
    backup_dir.rmdir()
    venv_dir.rename(backup_dir)
    return backup_dir


def _restore_reinstall_backup(venv_dir: Path, restore_venv_dir: Path, backup_dir: Path) -> None:
    rmdir(venv_dir)
    backup_dir.rename(restore_venv_dir)


def _get_reinstall_resource_paths(venv: Venv, local_bin_dir: Path, local_man_dir: Path) -> set[Path]:
    package_infos = _get_venv_package_infos(venv)
    resource_paths = _get_venv_resource_paths("app", venv.bin_path, local_bin_dir, package_infos)
    for man_section in MAN_SECTIONS:
        resource_paths |= _get_venv_resource_paths(
            "man", venv.man_path / man_section, local_man_dir / man_section, package_infos
        )
    return resource_paths


def _get_expected_reinstall_resource_paths(venv: Venv, local_bin_dir: Path, local_man_dir: Path) -> set[Path]:
    resource_paths: set[Path] = set()
    if not venv.pipx_metadata.exposure_enabled:
        return resource_paths
    for package_info in venv.package_metadata.values():
        for app_path in package_info.app_paths_to_expose:
            resource_paths.add(local_bin_dir / add_suffix(app_path.name, package_info.suffix))
        for man_path in package_info.man_paths_to_expose:
            resource_paths.add(local_man_dir / man_path.parent.name / man_path.name)
    return resource_paths


def _remove_stale_reinstall_resources(resource_paths: set[Path]) -> None:
    for path in sorted(resource_paths):
        try:
            safe_unlink(path)
            if path.is_symlink():
                path.unlink()
        except FileNotFoundError:
            pass


def reinstall(
    *,
    venv_dir: Path,
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str,
    verbose: bool,
    force_reinstall_shared_libs: bool = False,
    python_flag_passed: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
    venv_lock: BaseFileLock | None = None,
) -> OperationResult[ReinstallData]:
    if not venv_dir.exists():
        return _outcome(
            venv_dir.name,
            OutputMessage(f"Nothing to reinstall for {venv_dir.name} {sleep}"),
            exit_code=EXIT_CODE_REINSTALL_VENV_NONEXISTENT,
        )

    try:
        Path(python).relative_to(venv_dir)
    except ValueError:
        pass
    else:
        return _outcome(
            venv_dir.name,
            OutputMessage(
                f"{error} Error, the python executable would be deleted! Change it using the --python option "
                f"or PIPX_DEFAULT_PYTHON environment variable.",
                stream=OutputStream.STDERR,
                level=OutputLevel.ERROR,
            ),
            exit_code=EXIT_CODE_REINSTALL_INVALID_PYTHON,
        )

    venv = Venv(venv_dir, verbose=verbose, backend=backend, env_backend=env_backend)
    venv.check_upgrade_shared_libs(
        pip_args=venv.pipx_metadata.main_package.pip_args, verbose=verbose, force_upgrade=force_reinstall_shared_libs
    )

    if venv.pipx_metadata.main_package.package_or_url is not None:
        package_or_url = venv.pipx_metadata.main_package.package_or_url
    else:
        package_or_url = venv.main_package_name

    if venv.pipx_metadata.main_package.pinned:
        raise PipxError(f"{error} Package {venv_dir} is pinned. Run `pipx unpin {venv_dir.name}` to unpin it first.")

    old_resource_paths = _get_reinstall_resource_paths(venv, local_bin_dir, local_man_dir)
    original_venv_dir = venv_dir
    reinstall_backup_dir = _create_reinstall_backup(venv_dir)
    messages: list[OutputMessage] = [OutputMessage(f"uninstalled {venv.name}! {stars}")]

    # in case legacy original dir name
    venv_dir = venv_dir.with_name(canonicalize_name(venv_dir.name))

    try:
        # install main package first
        installed = install(
            venv_dir,
            [venv.main_package_name],
            [package_or_url],
            local_bin_dir,
            local_man_dir,
            python,
            venv.pipx_metadata.main_package.pip_args,
            venv.pipx_metadata.venv_args,
            verbose,
            force=True,
            reinstall=True,
            include_dependencies=venv.pipx_metadata.main_package.include_dependencies,
            include_resources_from=venv.pipx_metadata.main_package.include_resources_from,
            preinstall_packages=[],
            expected_apps=venv.pipx_metadata.main_package.expected_apps,
            lock_file=venv.pipx_metadata.main_package.lock_file,
            cooldown_days=venv.pipx_metadata.main_package.cooldown_days,
            suffix=venv.pipx_metadata.main_package.suffix,
            python_flag_passed=python_flag_passed,
            backend=backend or venv.pipx_metadata.backend,
            env_backend=env_backend,
            exposure_enabled=venv.pipx_metadata.exposure_enabled,
            venv_lock=venv_lock,
            emit_output=False,
        )
        # install does not raise when it does not render, so restore the backup on a failed result too
        if installed.errors:
            raise PipxError(installed.errors[0].message)
        messages.extend(installed.messages)

        # now install injected packages
        for injected_name, injected_package in venv.pipx_metadata.injected_packages.items():
            if injected_package.package_or_url is None:
                # This should never happen, but package_or_url is type
                #   Optional[str] so mypy thinks it could be None
                raise PipxError(f"Internal Error injecting package {injected_package} into {venv.name}")
            inject_dep(
                venv_dir,
                injected_name,
                injected_package.package_or_url,
                injected_package.pip_args,
                verbose=verbose,
                include_apps=injected_package.include_apps,
                include_dependencies=injected_package.include_dependencies,
                include_resources_from=injected_package.include_resources_from,
                force=True,
                backend=backend or venv.pipx_metadata.backend,
                env_backend=env_backend,
                cooldown_days=injected_package.cooldown_days,
            )

        new_resource_paths = _get_expected_reinstall_resource_paths(
            Venv(venv_dir, verbose=verbose), local_bin_dir, local_man_dir
        )
        _remove_stale_reinstall_resources(old_resource_paths - new_resource_paths)
    except (Exception, KeyboardInterrupt):
        _restore_reinstall_backup(venv_dir, original_venv_dir, reinstall_backup_dir)
        _LOGGER.error("%s Reinstall failed; restored %s.", error, venv.name)
        raise
    else:
        rmdir(reinstall_backup_dir)

    return OperationResult(
        command=("reinstall",),
        data=ReinstallData(environments=(_ReinstalledEnvironment(venv.name),)),
        messages=tuple(messages),
    )


def reinstall_all(
    venv_container: VenvContainer,
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str,
    verbose: bool,
    *,
    skip: Sequence[str],
    python_flag_passed: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
) -> OperationResult[ReinstallData]:
    errors: list[OperationError] = []
    reinstalled: list[_ReinstalledEnvironment] = []
    messages: list[OutputMessage] = []

    # iterate on all packages and reinstall them
    # for the first one, we also trigger
    # a reinstall of shared libs beforehand
    first_reinstall = True
    for venv_dir in venv_container.iter_venv_dirs():
        if venv_dir.name in skip:
            continue
        try:
            with venv_container.venv_lock(venv_dir) as venv_lock:
                outcome = reinstall(
                    venv_dir=venv_dir,
                    local_bin_dir=local_bin_dir,
                    local_man_dir=local_man_dir,
                    python=python,
                    verbose=verbose,
                    force_reinstall_shared_libs=first_reinstall,
                    python_flag_passed=python_flag_passed,
                    backend=backend,
                    env_backend=env_backend,
                    venv_lock=venv_lock,
                )
        except PipxError as error_raised:
            errors.append(
                OperationError(code="environment_reinstall_failed", message=str(error_raised), environment=venv_dir.name)
            )
            messages.append(OutputMessage(str(error_raised), stream=OutputStream.STDERR, level=OutputLevel.ERROR))
        else:
            first_reinstall = False
            reinstalled.append(_ReinstalledEnvironment(venv_dir.name))
            messages.extend(outcome.messages)
    if not reinstalled:
        messages.append(OutputMessage(f"No packages reinstalled after running 'pipx reinstall-all' {sleep}"))
    return OperationResult(
        command=("reinstall-all",),
        data=ReinstallData(environments=tuple(reinstalled)),
        messages=tuple(messages),
        exit_code=ExitCode(1) if errors else EXIT_CODE_OK,
        errors=tuple(errors),
        succeeded=bool(reinstalled),
    )


@dataclass(frozen=True)
class _ReinstalledEnvironment:
    environment: str


@dataclass(frozen=True)
class ReinstallData(OperationData):
    environments: tuple[_ReinstalledEnvironment, ...]


def _outcome(environment: str, message: OutputMessage, *, exit_code: ExitCode) -> OperationResult[ReinstallData]:
    return OperationResult(
        command=("reinstall",),
        data=ReinstallData(environments=()),
        messages=(message,),
        exit_code=exit_code,
        errors=(OperationError(code="environment_reinstall_failed", message=message.text, environment=environment),),
    )


__all__ = [
    "ReinstallData",
    "reinstall",
    "reinstall_all",
]
