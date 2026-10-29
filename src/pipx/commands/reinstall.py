from __future__ import annotations

__lazy_modules__ = [
    "contextlib",
    "functools",
    "packaging.utils",
    "pathlib",
    "pipx",
    "pipx.commands.common",
    "pipx.commands.inject",
    "pipx.commands.install",
    "pipx.commands.transaction",
    "pipx.commands.uninstall",
    "pipx.fanout",
    "pipx.package_specifier",
    "pipx.pipx_metadata_file",
    "pipx.util",
    "pipx.venv",
    "tempfile",
    "types",
]

import contextlib
import logging
import sys
import types
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from tempfile import mkdtemp
from typing import TYPE_CHECKING, Final

from packaging.utils import canonicalize_name

from pipx import paths
from pipx.commands.common import (
    add_suffix,
    drop_copies_claimed_elsewhere,
    drop_links_taken_over,
    expose_shared_resources_in_order,
    force_replaces_only,
)
from pipx.commands.inject import inject_dep
from pipx.commands.install import install
from pipx.commands.transaction import REINSTALL_BACKUP_SUFFIX, is_unfinished, rename_once_released
from pipx.commands.uninstall import _get_venv_package_infos, _get_venv_resource_paths
from pipx.constants import (
    COMPLETION_SECTIONS,
    EXIT_CODE_OK,
    EXIT_CODE_REINSTALL_INVALID_PYTHON,
    EXIT_CODE_REINSTALL_VENV_NONEXISTENT,
    MAN_SECTIONS,
    ExitCode,
)
from pipx.emojis import error, sleep, stars
from pipx.fanout import fan_out, locked_in_order, uninterrupted
from pipx.package_specifier import trusted_recorded_pip_args
from pipx.pipx_metadata_file import PIPX_INFO_FILENAME, PipxMetadata
from pipx.result import OperationData, OperationError, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.util import PipxError, redact_url_credentials, rmdir, safe_unlink
from pipx.venv import Venv, VenvContainer

if TYPE_CHECKING:
    from collections.abc import Sequence

    from filelock import BaseFileLock

    from pipx.pipx_metadata_file import PackageInfo

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def _create_reinstall_backup(venv_dir: Path) -> Path:
    # keep the backup in the trash rather than beside the venv, so it is not enumerated as a broken environment; the
    # trash shares the home's filesystem, so moving the venv there and back stays an atomic rename
    paths.ctx.trash.mkdir(parents=True, exist_ok=True)
    backup_dir = Path(mkdtemp(prefix=f"{venv_dir.name}-", suffix=REINSTALL_BACKUP_SUFFIX, dir=paths.ctx.trash))
    backup_dir.rmdir()
    rename_once_released(venv_dir, backup_dir)
    return backup_dir


def _restore_reinstall_backup(venv_dir: Path, restore_venv_dir: Path, backup_dir: Path) -> None:
    # a signal between the two steps would leave the venv deleted and its only copy in the trash
    with uninterrupted():
        rmdir(venv_dir)
        backup_dir.rename(restore_venv_dir)


def _get_reinstall_resource_paths(venv: Venv, local_bin_dir: Path, local_man_dir: Path) -> set[Path]:
    package_infos = _get_venv_package_infos(venv)
    resource_paths = _get_venv_resource_paths("app", venv.bin_path, local_bin_dir, package_infos)
    for man_section in MAN_SECTIONS:
        resource_paths |= _get_venv_resource_paths(
            "man", venv.man_path / man_section, local_man_dir / man_section, package_infos
        )
    for completion_section in COMPLETION_SECTIONS:
        resource_paths |= _get_venv_resource_paths(
            "completion",
            venv.man_path.parent / completion_section,
            paths.ctx.completion_dir / completion_section,
            package_infos,
        )
    return resource_paths


def _get_expected_reinstall_resource_paths(venv: Venv, local_bin_dir: Path, local_man_dir: Path) -> set[Path]:
    resource_paths: set[Path] = set()
    if not venv.pipx_metadata.exposure_enabled:
        return resource_paths
    for package_info in venv.package_metadata.values():
        resource_paths.update(
            local_bin_dir / add_suffix(app_path.name, package_info.suffix)
            for app_path in package_info.app_paths_to_expose
        )
        resource_paths.update(
            local_man_dir / man_path.parent.name / man_path.name for man_path in package_info.man_paths_to_expose
        )
        resource_paths.update(
            paths.ctx.completion_dir
            / completion_path.parent.parent.name
            / completion_path.parent.name
            / completion_path.name
            for completion_path in package_info.completion_paths_to_expose
        )
    return resource_paths


def _remove_stale_reinstall_resources(resource_paths: set[Path]) -> None:
    for path in sorted(resource_paths):
        _unlink_stale_resource(path)


def _unlink_stale_resource(path: Path) -> None:
    try:
        safe_unlink(path)
        if path.is_symlink():
            path.unlink()
    except FileNotFoundError:
        pass


def _raise_first_error(errors: tuple[OperationError, ...]) -> None:
    # install returns a failed result instead of raising, so surface it here to trigger the enclosing rollback
    if errors:
        msg = errors[0].message
        raise PipxError(msg)


def _require_injected_url(injected_package: PackageInfo, venv_name: str) -> str:
    # package_or_url is Optional[str] for mypy, though reinstall metadata always carries it
    if injected_package.package_or_url is None:
        msg = f"Internal Error injecting package {redact_url_credentials(str(injected_package))} into {venv_name}"
        raise PipxError(msg)
    return injected_package.package_or_url


def _unrecorded_package_spec(venv: Venv) -> str:
    # only pipx before 0.15.0.0 wrote no record, and it named the environment after the package inside; a killed install
    # or an unreadable record hides a spec, index and suffix the directory name cannot recover
    if not (venv.root / PIPX_INFO_FILENAME).exists() and not is_unfinished(venv.root):
        with contextlib.suppress(OSError):
            if venv.has_package(venv.main_package_name):
                return venv.main_package_name
    msg = (
        f"Not reinstalling {venv.name}. It has missing internal pipx metadata, so pipx cannot tell what it was "
        "installed from. Please uninstall and install this package to fix."
    )
    raise PipxError(msg)


def _resolve_self_reinstall_imports(venv_dir: Path) -> None:
    if Path(sys.prefix).resolve() != venv_dir.resolve() or not hasattr(types, "LazyImportType"):
        return

    # The running venv is about to move, so resolve imports that still need its source files.
    resolved: set[tuple[str, str]] = set()
    while pending := [
        (module, name)
        for module in tuple(sys.modules.values())
        if isinstance(module, types.ModuleType) and module.__name__.startswith("pipx.")
        for name, value in vars(module).items()
        if isinstance(value, types.LazyImportType) and (module.__name__, name) not in resolved
    ]:
        for module, name in pending:
            resolved.add((module.__name__, name))
            with contextlib.suppress(ImportError):
                getattr(module, name)


def reinstall(  # ruff:ignore[too-many-arguments]  # reinstall rebuilds a venv from its metadata and forwards the full install context
    *,
    venv_dir: Path,
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str,
    verbose: bool,
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
    # checked before the backup, so a refused source leaves the environment as it was
    main_pip_args: Final[list[str]] = trusted_recorded_pip_args(venv.pipx_metadata.main_package.pip_args, venv_dir)
    injected_pip_args: Final[dict[str, list[str]]] = {
        name: trusted_recorded_pip_args(package.pip_args, venv_dir)
        for name, package in venv.pipx_metadata.injected_packages.items()
    }
    venv.check_upgrade_shared_libs(pip_args=main_pip_args, verbose=verbose)

    if venv.pipx_metadata.main_package.package_or_url is not None:
        package_or_url = venv.pipx_metadata.main_package.package_or_url
    else:
        package_or_url = _unrecorded_package_spec(venv)

    if venv.pipx_metadata.main_package.pinned:
        msg = f"{error} Package {venv_dir} is pinned. Run `pipx unpin {venv_dir.name}` to unpin it first."
        raise PipxError(msg)

    old_resource_paths = _get_reinstall_resource_paths(venv, local_bin_dir, local_man_dir)
    original_venv_dir = venv_dir
    _resolve_self_reinstall_imports(venv_dir)
    reinstall_backup_dir = _create_reinstall_backup(venv_dir)
    messages: list[OutputMessage] = [OutputMessage(f"uninstalled {venv.name}! {stars}")]

    # in case legacy original dir name
    venv_dir = venv_dir.with_name(canonicalize_name(venv_dir.name))

    try:  # ruff:ignore[too-many-statements-in-try-clause]  # the whole rebuild must share one handler so any failure restores the backup
        with force_replaces_only(old_resource_paths):
            installed = install(
                venv_dir,
                [venv.main_package_name],
                [package_or_url],
                local_bin_dir,
                local_man_dir,
                python,
                main_pip_args,
                venv.pipx_metadata.venv_args,
                verbose=verbose,
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
            _raise_first_error(installed.errors)
            messages.extend(installed.messages)

            for injected_name, injected_package in venv.pipx_metadata.injected_packages.items():
                injected = inject_dep(
                    venv_dir,
                    injected_name,
                    _require_injected_url(injected_package, venv.name),
                    injected_pip_args[injected_name],
                    verbose=verbose,
                    include_apps=injected_package.include_apps,
                    include_dependencies=injected_package.include_dependencies,
                    include_resources_from=injected_package.include_resources_from,
                    force=True,
                    # the venv was just rebuilt, and --force-reinstall would also refetch the main package by name from
                    # the injected package's index when the injected package depends on it
                    force_reinstall=False,
                    suffix=injected_package.suffix == venv.pipx_metadata.main_package.suffix,
                    backend=backend or venv.pipx_metadata.backend,
                    env_backend=env_backend,
                    cooldown_days=injected_package.cooldown_days,
                    pinned=injected_package.pinned,
                    emit_output=False,
                )
                messages.extend(injected.messages)

        new_resource_paths = _get_expected_reinstall_resource_paths(
            Venv(venv_dir, verbose=verbose), local_bin_dir, local_man_dir
        )
        _remove_stale_reinstall_resources(
            drop_links_taken_over(
                drop_copies_claimed_elsewhere(old_resource_paths - new_resource_paths, venv.bin_path),
                original_venv_dir,
                venv_dir,
            )
        )
    except PipxError:
        _restore_reinstall_backup(venv_dir, original_venv_dir, reinstall_backup_dir)
        # an expected failure (e.g. pip could not install the package) that the CLI reports itself, so like the CLI
        # entry point keep its traceback for debug output
        _LOGGER.error("%s Reinstall failed; restored %s.", error, venv.name)  # ruff:ignore[error-instead-of-exception]
        _LOGGER.debug("Reinstall failure", exc_info=True)
        raise
    except KeyboardInterrupt:
        _restore_reinstall_backup(venv_dir, original_venv_dir, reinstall_backup_dir)
        _LOGGER.error("%s Interrupted; restored %s.", error, venv.name)  # ruff:ignore[error-instead-of-exception]
        raise
    except Exception:
        _restore_reinstall_backup(venv_dir, original_venv_dir, reinstall_backup_dir)
        _LOGGER.exception("%s Reinstall failed; restored %s.", error, venv.name)
        raise
    else:
        rmdir(reinstall_backup_dir)

    return OperationResult(
        command=("reinstall",),
        data=ReinstallData(environments=(_ReinstalledEnvironment(venv.name),)),
        messages=tuple(messages),
    )


def reinstall_all(  # ruff:ignore[too-many-arguments]  # reinstall-all forwards the full reinstall context to every environment
    venv_container: VenvContainer,
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str,
    *,
    verbose: bool,
    skip: Sequence[str],
    python_flag_passed: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
) -> OperationResult[ReinstallData]:
    errors: list[OperationError] = []
    reinstalled: list[_ReinstalledEnvironment] = []
    messages: list[OutputMessage] = []

    venv_dirs: Final[list[Path]] = [
        venv_dir for venv_dir in venv_container.iter_venv_dirs() if venv_dir.name not in skip
    ]
    with expose_shared_resources_in_order(
        (PipxMetadata(venv_dir) for venv_dir in venv_dirs), local_bin_dir, local_man_dir
    ):
        outcomes: Final[list[OperationResult[ReinstallData]]] = fan_out(
            [
                partial(
                    _reinstall_locked,
                    venv_container,
                    venv_dir,
                    local_bin_dir=local_bin_dir,
                    local_man_dir=local_man_dir,
                    python=python,
                    verbose=verbose,
                    python_flag_passed=python_flag_passed,
                    backend=backend,
                    env_backend=env_backend,
                )
                for venv_dir in venv_dirs
            ],
            sequential=verbose,
        )
    for outcome in outcomes:
        errors.extend(outcome.errors)
        messages.extend(outcome.messages)
        if not outcome.errors:
            reinstalled.extend(outcome.data.environments)
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


def _reinstall_locked(  # ruff:ignore[too-many-arguments]  # forwards the full reinstall context for one environment
    venv_container: VenvContainer,
    venv_dir: Path,
    *,
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str,
    verbose: bool,
    python_flag_passed: bool,
    backend: str | None,
    env_backend: str | None,
) -> OperationResult[ReinstallData]:
    try:
        with locked_in_order(venv_container.venv_lock(venv_dir)) as venv_lock:
            return reinstall(
                venv_dir=venv_dir,
                local_bin_dir=local_bin_dir,
                local_man_dir=local_man_dir,
                python=python,
                verbose=verbose,
                python_flag_passed=python_flag_passed,
                backend=backend,
                env_backend=env_backend,
                venv_lock=venv_lock,
            )
    except PipxError as error_raised:
        return OperationResult(
            command=("reinstall",),
            data=ReinstallData(environments=()),
            messages=(OutputMessage(str(error_raised), stream=OutputStream.STDERR, level=OutputLevel.ERROR),),
            exit_code=ExitCode(1),
            errors=(
                OperationError(
                    code="environment_reinstall_failed", message=str(error_raised), environment=venv_dir.name
                ),
            ),
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
