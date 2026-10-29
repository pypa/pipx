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
    "pipx.fanout",
    "pipx.options",
    "pipx.package_specifier",
    "pipx.pipx_metadata_file",
    "pipx.redact",
    "pipx.trash",
    "pipx.util",
    "pipx.venv",
    "tempfile",
]

import contextlib
import logging
from dataclasses import dataclass, replace
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
    get_venv_package_infos,
    get_venv_resource_paths,
    give_back_shared_links,
)
from pipx.commands.inject import inject_dep
from pipx.commands.install import install
from pipx.commands.transaction import (
    REINSTALL_BACKUP_SUFFIX,
    import_from_copy,
    is_unfinished,
    release_copy,
    rename_once_released,
    repoint_imports,
    runs_from_venv,
)
from pipx.constants import (
    COMPLETION_SECTIONS,
    EXIT_CODE_OK,
    EXIT_CODE_REINSTALL_INVALID_PYTHON,
    EXIT_CODE_REINSTALL_VENV_NONEXISTENT,
    MAN_SECTIONS,
    ExitCode,
)
from pipx.emojis import ERROR, SLEEP, STARS
from pipx.fanout import fan_out, locked_in_order, uninterrupted
from pipx.options import CooldownOptions, ExposureOptions, InjectOptions, InstallOptions
from pipx.package_specifier import trusted_recorded_pip_args
from pipx.pipx_metadata_file import PIPX_INFO_FILENAME, PipxMetadata
from pipx.redact import redact_url_credentials
from pipx.result import OperationData, OperationError, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.trash import rmdir, safe_unlink
from pipx.util import PipxError
from pipx.venv import Venv, VenvContainer

if TYPE_CHECKING:
    from filelock import BaseFileLock

    from pipx.options import ReinstallOptions
    from pipx.pipx_metadata_file import PackageInfo

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def reinstall_all(venv_container: VenvContainer, options: ReinstallOptions) -> OperationResult[ReinstallData]:
    venv_dirs: Final[list[Path]] = [
        venv_dir for venv_dir in venv_container.iter_venv_dirs() if venv_dir.name not in options.skip
    ]
    with expose_shared_resources_in_order(
        (PipxMetadata(venv_dir) for venv_dir in venv_dirs), options.local_bin_dir, options.local_man_dir
    ):
        outcomes: Final[list[OperationResult[ReinstallData]]] = fan_out(
            [partial(_reinstall_locked, venv_container, venv_dir, options) for venv_dir in venv_dirs],
            sequential=options.verbose,
        )
    errors: Final[list[OperationError]] = []
    messages: Final[list[OutputMessage]] = []
    reinstalled: Final[list[_ReinstalledEnvironment]] = []
    for outcome in outcomes:
        errors.extend(outcome.errors)
        messages.extend(outcome.messages)
        if not outcome.errors:
            reinstalled.extend(outcome.data.environments)
    if not reinstalled:
        messages.append(OutputMessage(text=f"No packages reinstalled after running 'pipx reinstall-all' {SLEEP}"))
    return OperationResult(
        command=("reinstall-all",),
        data=ReinstallData(environments=tuple(reinstalled)),
        messages=tuple(messages),
        exit_code=ExitCode(1) if errors else EXIT_CODE_OK,
        errors=tuple(errors),
        succeeded=bool(reinstalled),
    )


def _reinstall_locked(
    venv_container: VenvContainer, venv_dir: Path, options: ReinstallOptions
) -> OperationResult[ReinstallData]:
    try:
        with locked_in_order(venv_container.venv_lock(venv_dir)) as venv_lock:
            return reinstall(venv_dir, options, venv_lock=venv_lock)
    except PipxError as error_raised:
        return OperationResult(
            command=("reinstall",),
            data=ReinstallData(environments=()),
            messages=(OutputMessage(text=str(error_raised), stream=OutputStream.STDERR, level=OutputLevel.ERROR),),
            exit_code=ExitCode(1),
            errors=(
                OperationError(
                    code="environment_reinstall_failed", message=str(error_raised), environment=venv_dir.name
                ),
            ),
        )


def reinstall(
    venv_dir: Path, options: ReinstallOptions, *, venv_lock: BaseFileLock | None
) -> OperationResult[ReinstallData]:
    if not venv_dir.exists():
        return _outcome(
            venv_dir.name,
            OutputMessage(text=f"Nothing to reinstall for {venv_dir.name} {SLEEP}"),
            exit_code=EXIT_CODE_REINSTALL_VENV_NONEXISTENT,
        )

    try:
        Path(options.python).relative_to(venv_dir)
    except ValueError:
        pass
    else:
        return _outcome(
            venv_dir.name,
            OutputMessage(
                text=f"{ERROR} Error, the python executable would be deleted! Change it using the --python option "
                f"or PIPX_DEFAULT_PYTHON environment variable.",
                stream=OutputStream.STDERR,
                level=OutputLevel.ERROR,
            ),
            exit_code=EXIT_CODE_REINSTALL_INVALID_PYTHON,
        )

    venv: Final[Venv] = Venv(venv_dir, verbose=options.verbose, backend=options.backend)
    # checked before the backup, so a refused source leaves the environment as it was
    main_pip_args: Final[list[str]] = trusted_recorded_pip_args(venv.pipx_metadata.main_package.pip_args, venv_dir)
    injected_pip_args: Final[dict[str, list[str]]] = {
        name: trusted_recorded_pip_args(package.pip_args, venv_dir)
        for name, package in venv.pipx_metadata.injected_packages.items()
    }
    venv.check_upgrade_shared_libs(pip_args=main_pip_args, verbose=options.verbose)

    package_or_url: Final[str] = (
        venv.pipx_metadata.main_package.package_or_url
        if venv.pipx_metadata.main_package.package_or_url is not None
        else _unrecorded_package_spec(venv)
    )

    if venv.pipx_metadata.main_package.pinned:
        msg: Final[str] = f"{ERROR} Package {venv_dir} is pinned. Run `pipx unpin {venv_dir.name}` to unpin it first."
        raise PipxError(msg)

    old_resource_paths: Final[set[Path]] = _get_reinstall_resource_paths(
        venv, options.local_bin_dir, options.local_man_dir
    )
    running: Final[bool] = runs_from_venv(venv_dir)
    reinstall_backup_dir: Final[Path] = _create_reinstall_backup(venv_dir)
    if running:
        import_from_copy(reinstall_backup_dir)
    messages: Final[list[OutputMessage]] = [OutputMessage(text=f"uninstalled {venv.name}! {STARS}")]

    # a legacy environment directory can carry a name that is not canonical; the rebuild uses the canonical one
    canonical_venv_dir: Final[Path] = venv_dir.with_name(canonicalize_name(venv_dir.name))

    try:  # ruff:ignore[too-many-statements-in-try-clause]  # the whole rebuild must share one handler so any failure restores the backup
        with force_replaces_only(old_resource_paths):
            installed: Final = install(
                canonical_venv_dir,
                [venv.main_package_name],
                [package_or_url],
                InstallOptions(
                    local_bin_dir=options.local_bin_dir,
                    local_man_dir=options.local_man_dir,
                    python=options.python,
                    pip_args=main_pip_args,
                    venv_args=venv.pipx_metadata.venv_args,
                    verbose=options.verbose,
                    force=True,
                    reinstall=True,
                    exposure=ExposureOptions(
                        include_dependencies=venv.pipx_metadata.main_package.include_dependencies,
                        include_resources_from=venv.pipx_metadata.main_package.include_resources_from,
                        suffix=venv.pipx_metadata.main_package.suffix,
                    ),
                    preinstall_packages=[],
                    expected_apps=venv.pipx_metadata.main_package.expected_apps,
                    lock_file=venv.pipx_metadata.main_package.lock_file,
                    cooldown=CooldownOptions(cli_days=venv.pipx_metadata.main_package.cooldown_days),
                    python_flag_passed=options.python_flag_passed,
                    backend=(
                        recorded_backend := replace(
                            options.backend, cli=options.backend.cli or venv.pipx_metadata.backend
                        )
                    ),
                    exposure_enabled=venv.pipx_metadata.exposure_enabled,
                    emit_output=False,
                ),
                venv_lock=venv_lock,
            )
            # install does not raise when it does not render, so restore the backup on a failed result too
            _raise_first_error(installed.errors)
            messages.extend(installed.messages)

            for injected_name, injected_package in venv.pipx_metadata.injected_packages.items():
                injected: Final = inject_dep(
                    canonical_venv_dir,
                    injected_name,
                    _require_injected_url(injected_package, venv.name),
                    InjectOptions(
                        pip_args=injected_pip_args[injected_name],
                        verbose=options.verbose,
                        include_apps=injected_package.include_apps,
                        include_dependencies=injected_package.include_dependencies,
                        include_resources_from=injected_package.include_resources_from,
                        force=True,
                        # the venv was just rebuilt, and --force-reinstall would also refetch the main package by name
                        # from the injected package's index when the injected package depends on it
                        force_reinstall=False,
                        with_suffix=injected_package.suffix == venv.pipx_metadata.main_package.suffix,
                        backend=recorded_backend,
                        cooldown_days=injected_package.cooldown_days,
                        pinned=injected_package.pinned,
                        emit_output=False,
                    ),
                )
                messages.extend(injected.messages)

        new_resource_paths: Final[set[Path]] = _get_expected_reinstall_resource_paths(
            Venv(canonical_venv_dir, verbose=options.verbose), options.local_bin_dir, options.local_man_dir
        )
        _remove_stale_reinstall_resources(
            drop_links_taken_over(
                drop_copies_claimed_elsewhere(old_resource_paths - new_resource_paths, venv.bin_path),
                venv_dir,
                canonical_venv_dir,
            )
        )
    except PipxError:
        _restore_reinstall_backup(canonical_venv_dir, venv_dir, reinstall_backup_dir)
        give_back_shared_links(old_resource_paths, venv_dir)
        # an expected failure (pip could not install the package, say) that the CLI reports itself, so like the CLI
        # entry point keep its traceback for debug output
        _LOGGER.error("%s Reinstall failed; restored %s.", ERROR, venv.name)  # ruff:ignore[error-instead-of-exception]
        _LOGGER.debug("Reinstall failure", exc_info=True)
        raise
    except KeyboardInterrupt:
        _restore_reinstall_backup(canonical_venv_dir, venv_dir, reinstall_backup_dir)
        give_back_shared_links(old_resource_paths, venv_dir)
        _LOGGER.error("%s Interrupted; restored %s.", ERROR, venv.name)  # ruff:ignore[error-instead-of-exception]
        raise
    except Exception:
        _restore_reinstall_backup(canonical_venv_dir, venv_dir, reinstall_backup_dir)
        give_back_shared_links(old_resource_paths, venv_dir)
        _LOGGER.exception("%s Reinstall failed; restored %s.", ERROR, venv.name)
        raise
    else:
        # the running pipx keeps importing from the backup, so the trash cleanup of the next pipx run removes it
        if not running:
            rmdir(reinstall_backup_dir)

    return OperationResult(
        command=("reinstall",),
        data=ReinstallData(environments=(_ReinstalledEnvironment(environment=venv.name),)),
        messages=tuple(messages),
    )


def _outcome(environment: str, message: OutputMessage, *, exit_code: ExitCode) -> OperationResult[ReinstallData]:
    return OperationResult(
        command=("reinstall",),
        data=ReinstallData(environments=()),
        messages=(message,),
        exit_code=exit_code,
        errors=(OperationError(code="environment_reinstall_failed", message=message.text, environment=environment),),
    )


def _unrecorded_package_spec(venv: Venv) -> str:
    # only pipx before 0.15.0.0 wrote no record, and it named the environment after the package inside; a killed install
    # or an unreadable record hides a spec, index and suffix the directory name cannot recover
    if not (venv.root / PIPX_INFO_FILENAME).exists() and not is_unfinished(venv.root):
        with contextlib.suppress(OSError):
            if venv.has_package(venv.main_package_name):
                return venv.main_package_name
    msg: Final[str] = (
        f"Not reinstalling {venv.name}. It has no internal pipx metadata, so pipx cannot tell what it was "
        "installed from. Uninstall and install this package to fix it."
    )
    raise PipxError(msg)


def _get_reinstall_resource_paths(venv: Venv, local_bin_dir: Path, local_man_dir: Path) -> set[Path]:
    package_infos: Final[tuple[PackageInfo, ...] | None] = get_venv_package_infos(venv)
    return get_venv_resource_paths("app", venv.bin_path, local_bin_dir, package_infos).union(
        *(
            get_venv_resource_paths("man", venv.man_path / section, local_man_dir / section, package_infos)
            for section in MAN_SECTIONS
        ),
        *(
            get_venv_resource_paths(
                "completion", venv.man_path.parent / section, paths.CTX.completion_dir / section, package_infos
            )
            for section in COMPLETION_SECTIONS
        ),
    )


def _create_reinstall_backup(venv_dir: Path) -> Path:
    # keep the backup in the trash rather than beside the venv, so it is not enumerated as a broken environment; the
    # trash shares the home's filesystem, so moving the venv there and back stays an atomic rename
    paths.CTX.trash.mkdir(parents=True, exist_ok=True)
    backup_dir: Final[Path] = Path(
        mkdtemp(prefix=f"{venv_dir.name}-", suffix=REINSTALL_BACKUP_SUFFIX, dir=paths.CTX.trash)
    )
    backup_dir.rmdir()
    rename_once_released(venv_dir, backup_dir)
    return backup_dir


def _raise_first_error(errors: tuple[OperationError, ...]) -> None:
    # raising from a helper keeps the raise out of the caller's try block
    if errors:
        raise PipxError(errors[0].message)


def _require_injected_url(injected_package: PackageInfo, venv_name: str) -> str:
    # the record types package_or_url as optional, though reinstall metadata always carries it
    if injected_package.package_or_url is None:
        msg: Final[str] = (
            f"Internal Error injecting package {redact_url_credentials(str(injected_package))} into {venv_name}"
        )
        raise PipxError(msg)
    return injected_package.package_or_url


def _get_expected_reinstall_resource_paths(venv: Venv, local_bin_dir: Path, local_man_dir: Path) -> set[Path]:
    if not venv.pipx_metadata.exposure_enabled:
        return set()
    resource_paths: Final[set[Path]] = set()
    for package_info in venv.package_metadata.values():
        resource_paths.update(
            local_bin_dir / add_suffix(app_path.name, package_info.suffix)
            for app_path in package_info.app_paths_to_expose
        )
        resource_paths.update(
            local_man_dir / man_path.parent.name / man_path.name for man_path in package_info.man_paths_to_expose
        )
        resource_paths.update(
            paths.CTX.completion_dir
            / completion_path.parent.parent.name
            / completion_path.parent.name
            / completion_path.name
            for completion_path in package_info.completion_paths_to_expose
        )
    return resource_paths


def _remove_stale_reinstall_resources(resource_paths: set[Path]) -> None:
    for path in sorted(resource_paths):
        with contextlib.suppress(FileNotFoundError):
            safe_unlink(path)
            if path.is_symlink():
                path.unlink()


def _restore_reinstall_backup(venv_dir: Path, restore_venv_dir: Path, backup_dir: Path) -> None:
    # a signal between the two steps would leave the venv deleted and its only copy in the trash
    with uninterrupted():
        rmdir(venv_dir)
        release_copy(backup_dir)
        backup_dir.rename(restore_venv_dir)
        repoint_imports(backup_dir, restore_venv_dir)


@dataclass(frozen=True, slots=True, kw_only=True)
class _ReinstalledEnvironment:
    environment: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ReinstallData(OperationData):
    environments: tuple[_ReinstalledEnvironment, ...]


__all__ = [
    "ReinstallData",
    "reinstall",
    "reinstall_all",
]
