from __future__ import annotations

__lazy_modules__ = [
    "functools",
    "json",
    "packaging.utils",
    "pipx",
    "pipx.backends",
    "pipx.commands.common",
    "pipx.commands.inject",
    "pipx.commands.transaction",
    "pipx.fanout",
    "pipx.interpreter",
    "pipx.package_specifier",
    "pipx.pipx_metadata_file",
    "pipx.requires_python",
    "pipx.script",
    "pipx.util",
    "pipx.venv",
]

import json
import logging
import re
import sys
from dataclasses import dataclass, replace
from functools import partial
from typing import TYPE_CHECKING, Final

from packaging.utils import canonicalize_name

from pipx import paths
from pipx.backends import PIP
from pipx.commands.common import (
    expose_package_resources,
    expose_shared_resources_in_order,
    get_expected_venv_resource_paths,
    locked_package_message,
    package_name_from_spec,
    remove_stale_venv_resources,
    run_post_install_actions,
    validate_expected_apps,
    validate_suffix,
)
from pipx.commands.inject import inject
from pipx.commands.transaction import VenvBackup, marked_unfinished, preserve_venv
from pipx.constants import (
    EXIT_CODE_OK,
    ExitCode,
    FetchPythonOptions,
)
from pipx.emojis import hazard, sleep
from pipx.fanout import fan_out, locked_in_order
from pipx.interpreter import get_default_python
from pipx.package_specifier import package_spec_satisfied, trusted_recorded_pip_args
from pipx.pipx_metadata_file import PackageInfo, PipxMetadata, load_spec_file
from pipx.requires_python import IncompatiblePythonError, interpreter_for
from pipx.result import (
    OperationData,
    OperationError,
    OperationResult,
    OutputFormat,
    OutputLevel,
    OutputMessage,
    OutputStream,
    render_messages,
    render_result,
)
from pipx.script import script_name_from_spec
from pipx.util import PipxError, pipx_wrap, redact_url_credentials, rmdir
from pipx.venv import Venv, VenvContainer

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path

    from filelock import BaseFileLock
    from packaging.specifiers import SpecifierSet

    from pipx.venv_inspect import VenvMetadata

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
_PYLOCK_NAME_RE: Final[re.Pattern[str]] = re.compile(r"pylock(?:\.[^.]+)?\.toml")
# value-taking options a recorded snapshot may carry, as their (uv, pip) spellings
_VALUE_OPTION_SPELLINGS: Final[dict[str, tuple[str, str]]] = {
    **dict.fromkeys(("--default-index", "--index-url", "-i"), ("--default-index", "--index-url")),
    **dict.fromkeys(("--index", "--extra-index-url"), ("--index", "--extra-index-url")),
    **dict.fromkeys(("--find-links", "-f"), ("--find-links", "--find-links")),
    **dict.fromkeys(("--constraints", "--constraint", "-c"), ("--constraints", "--constraint")),
    **dict.fromkeys(("--allow-insecure-host", "--trusted-host"), ("--allow-insecure-host", "--trusted-host")),
    **{option: (option, option) for option in ("--keyring-provider", "--index-strategy", "--prerelease")},
}


def install(  # ruff:ignore[too-many-arguments, too-many-positional-arguments, too-many-branches, too-many-locals, too-many-statements]  # flat install API mirroring the CLI's install options
    venv_dir: Path | None,
    package_names: list[str] | None,
    package_specs: list[str],
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str | None,
    pip_args: list[str],
    venv_args: list[str],
    *,
    verbose: bool,
    force: bool,
    reinstall: bool,
    include_dependencies: bool,
    include_resources_from: Sequence[str],
    preinstall_packages: list[str] | None,
    expected_apps: Sequence[str] = (),
    lock_file: Path | None = None,
    suffix: str = "",
    python_flag_passed: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
    exposure_enabled: bool | None = None,
    upgrade: bool = False,
    upgrade_strategy: str | None = None,
    cooldown_days: int | None = None,
    env_cooldown_days: int | None = None,
    venv_lock: BaseFileLock | None = None,
    pinned: bool | None = None,
    preserve_existing: bool = False,
    fetch_python: FetchPythonOptions = FetchPythonOptions.NEVER,
    replace_expected_apps: bool = False,
    replace_lock: bool = False,
    emit_output: bool = True,
) -> OperationResult[InstallData]:
    validate_suffix(suffix)
    messages: Final[list[OutputMessage]] = []
    packages: Final[list[_InstalledPackage]] = []
    skipped: Final[list[_SkippedInstall]] = []
    failures: Final[list[_FailedInstall]] = []
    try:
        lock_file, python = _prepare_install(
            package_specs,
            python,
            lock_file,
            expected_apps,
            preinstall_packages,
            cooldown_days=cooldown_days,
            upgrade=upgrade,
            upgrade_strategy=upgrade_strategy,
        )
    except PipxError as error:
        return _finish_install(_failed_install_result(package_specs[0], error), emit_output=emit_output)

    # a lock file already pins every version, so PIPX_COOLDOWN has nothing left to constrain
    resolution_cooldown: Final[int | None] = (
        None if lock_file is not None else _first_cooldown(cooldown_days, env_cooldown_days)
    )
    package_names, resolution_failure, interpreters = _resolve_package_names(
        package_names,
        package_specs,
        python,
        pip_args,
        tuple(expected_apps),
        verbose=verbose,
        backend=backend,
        env_backend=env_backend,
        cooldown_days=resolution_cooldown,
        fetch_python=fetch_python,
        python_flag_passed=python_flag_passed,
        messages=messages,
    )
    if resolution_failure is not None:
        package_spec, resolution_error = resolution_failure
        return _finish_install(_failed_install_result(package_spec, resolution_error), emit_output=emit_output)

    venv_container: Final[VenvContainer] = VenvContainer(venv_dir.parent if venv_dir is not None else paths.ctx.venvs)
    for package_name, package_spec, package_python in zip(package_names, package_specs, interpreters, strict=False):
        if venv_dir is None:
            venv_dir = venv_container.get_venv_dir(f"{package_name}{suffix}")
        environment = venv_dir.name

        with venv_lock or venv_container.venv_lock(venv_dir):
            try:
                exists = venv_dir.exists() and bool(next(venv_dir.iterdir()))
            except StopIteration:
                exists = False

            # ``pipx install pip`` always uses pip (uv venvs ship no pip). Override
            # only the implicit env path; ``--backend uv`` still falls through to
            # ``assert_not_pip_under_uv`` so an explicit conflict fails loudly.
            install_backend, install_env_backend = backend, env_backend
            if canonicalize_name(package_name) == "pip":
                install_backend = backend or PIP
                install_env_backend = None

            try:  # ruff:ignore[too-many-statements-in-try-clause]  # one PipxError handler must cover the whole existing-venv resolution
                venv = Venv(
                    venv_dir,
                    python=package_python,
                    verbose=verbose,
                    backend=install_backend,
                    env_backend=install_env_backend,
                )
                required_apps = tuple(
                    dict.fromkeys(
                        expected_apps
                        if replace_expected_apps
                        else expected_apps or venv.pipx_metadata.main_package.expected_apps
                    )
                )
                recorded_lock = venv.pipx_metadata.main_package.lock_file
                required_lock = lock_file if replace_lock else lock_file or recorded_lock
                required_cooldown = _resolve_cooldown(
                    required_lock,
                    cooldown_days,
                    venv.pipx_metadata.main_package.cooldown_days,
                    modifies_existing=exists and force,
                    env_cooldown_days=env_cooldown_days,
                )
                required_exposure = (
                    venv.pipx_metadata.exposure_enabled if exposure_enabled is None else exposure_enabled
                )
                required_pinned = venv.pipx_metadata.main_package.pinned if pinned is None else pinned
                if exists:
                    existing = _handle_existing_install(
                        venv,
                        package_name,
                        package_spec,
                        local_bin_dir,
                        local_man_dir,
                        python=package_python,
                        pip_args=pip_args,
                        verbose=verbose,
                        force=force,
                        reinstall=reinstall,
                        upgrade=upgrade,
                        python_flag_passed=python_flag_passed,
                        upgrade_strategy=upgrade_strategy,
                        expected_apps=required_apps,
                        cooldown_days=required_cooldown,
                    )
                    messages.extend(existing.messages)
                    packages.extend(existing.packages)
                    skipped.extend(existing.skipped)
                    if not existing.continue_install:
                        venv_dir = None
                        continue
                    # --force reuses the environment, so --python does not switch it; `pipx reinstall --python` does
                    if (
                        python_flag_passed
                        and (recorded := venv.pipx_metadata.source_interpreter) is not None
                        and recorded.is_file()
                    ):
                        venv.python = str(recorded)
            except PipxError as error:
                _record_install_failure(failures, messages, environment, error)
                break

            previous_resource_paths: set[Path] = get_expected_venv_resource_paths(venv, local_bin_dir, local_man_dir)
            preserve_existing_venv = exists and (
                preserve_existing or bool(required_apps or include_resources_from) or required_lock is not None
            )
            try:  # ruff:ignore[too-many-statements-in-try-clause]  # one handler must roll back the whole build-and-expose sequence on failure
                with preserve_venv(venv_dir, enabled=exists, copy_upfront=preserve_existing_venv) as venv_backup:
                    venv.check_upgrade_shared_libs(pip_args=pip_args, verbose=verbose)
                    if exists and (required_lock is not None or (replace_lock and recorded_lock is not None)):
                        rmdir(venv_dir)
                        venv = Venv(venv_dir, python=venv.python, verbose=verbose, backend=venv.backend_name)
                    build = _EnvironmentBuild(
                        venv_args=venv_args,
                        pip_args=pip_args,
                        override_shared=canonicalize_name(package_name) == "pip",
                        exposure_enabled=required_exposure,
                        preinstall_packages=preinstall_packages,
                        package_name=package_name,
                        package_spec=package_spec,
                        force_reinstall=force and exists,
                        include_dependencies=include_dependencies,
                        include_resources_from=include_resources_from,
                        suffix=suffix,
                        expected_apps=required_apps,
                        lock_file=required_lock,
                        cooldown_days=required_cooldown,
                        pinned=required_pinned,
                    )
                    venv = _install_on_supported_python(
                        venv,
                        build,
                        venv_dir=venv_dir,
                        venv_backup=venv_backup,
                        fetch_python=fetch_python,
                        python_flag_passed=python_flag_passed,
                        verbose=verbose,
                        messages=messages,
                    )
                    validate_expected_apps(venv, package_name, required_apps)
                    messages.extend(
                        run_post_install_actions(
                            venv,
                            package_name,
                            local_bin_dir,
                            local_man_dir,
                            venv_dir,
                            force=force,
                            previous_resource_paths=previous_resource_paths,
                        )
                    )
            except (Exception, KeyboardInterrupt) as error:
                if not exists:
                    venv.remove_venv()
                if not isinstance(error, PipxError):
                    raise
                _record_install_failure(failures, messages, venv.name, error)
                break
            packages.append(_installed_package(venv, package_name))
        venv_dir = None

    return _finish_install(
        OperationResult(
            command=("install",),
            data=InstallData(packages=tuple(packages), skipped=tuple(skipped)),
            messages=tuple(messages),
            exit_code=ExitCode(1 if failures else 0),
            errors=tuple(
                OperationError(code="package_install_failed", message=f.error, environment=f.environment)
                for f in failures
            ),
            succeeded=bool(packages or skipped),
        ),
        emit_output=emit_output,
    )


def _prepare_install(  # ruff:ignore[too-many-arguments]  # forwards the flat install option set to validation
    package_specs: list[str],
    python: str | None,
    lock_file: Path | None,
    expected_apps: Sequence[str],
    preinstall_packages: Sequence[str] | None,
    *,
    cooldown_days: int | None,
    upgrade: bool,
    upgrade_strategy: str | None,
) -> tuple[Path | None, str]:
    lock_file = _validate_install_options(
        package_specs,
        expected_apps,
        preinstall_packages,
        lock_file,
        cooldown_days,
        upgrade=upgrade,
        upgrade_strategy=upgrade_strategy,
    )
    return lock_file, python or get_default_python()


def _resolve_package_names(  # ruff:ignore[too-many-arguments]  # forwards the flat resolver context for each spec
    package_names: list[str] | None,
    package_specs: list[str],
    python: str,
    pip_args: list[str],
    expected_apps: tuple[str, ...],
    *,
    verbose: bool,
    backend: str | None,
    env_backend: str | None,
    cooldown_days: int | None,
    fetch_python: FetchPythonOptions,
    python_flag_passed: bool,
    messages: list[OutputMessage],
) -> tuple[list[str], tuple[str, PipxError] | None, list[str]]:
    if package_names is not None and len(package_names) == len(package_specs):
        return package_names, None, [python] * len(package_specs)

    resolved: Final[list[str]] = []
    interpreters: Final[list[str]] = []
    for package_spec in package_specs:
        interpreter = python
        try:  # ruff:ignore[too-many-statements-in-try-clause]  # one PipxError handler must cover the whole per-spec name resolution
            if (script_name := script_name_from_spec(package_spec, expected_apps)) is not None:
                resolved.append(script_name)
                interpreters.append(interpreter)
                continue
            try:
                name = package_name_from_spec(
                    package_spec,
                    interpreter,
                    pip_args=pip_args,
                    verbose=verbose,
                    backend=backend,
                    env_backend=env_backend,
                    cooldown_days=cooldown_days,
                )
            except IncompatiblePythonError as error:
                # reading the name off a local project already runs an install, so the constraint surfaces here first
                interpreter = _supported_python(
                    error.constraint,
                    fetch_python=fetch_python,
                    python_flag_passed=python_flag_passed,
                    messages=messages,
                )
                name = package_name_from_spec(
                    package_spec,
                    interpreter,
                    pip_args=pip_args,
                    verbose=verbose,
                    backend=backend,
                    env_backend=env_backend,
                    cooldown_days=cooldown_days,
                )
            resolved.append(name)
            interpreters.append(interpreter)
        except PipxError as error:
            return resolved, (package_spec, error), interpreters
    return resolved, None, interpreters


def _validate_install_options(  # ruff:ignore[too-many-arguments]  # validates the flat set of install options together
    package_specs: Sequence[str],
    expected_apps: Sequence[str],
    preinstall_packages: Sequence[str] | None,
    lock_file: Path | None,
    cooldown_days: int | None,
    *,
    upgrade: bool,
    upgrade_strategy: str | None,
) -> Path | None:
    if upgrade_strategy is not None and not upgrade:
        msg = "--upgrade-strategy requires --upgrade"
        raise PipxError(msg)
    if expected_apps and len(package_specs) != 1:
        msg = "--app accepts one package spec"
        raise PipxError(msg)
    if lock_file is None:
        return None
    if len(package_specs) != 1:
        msg = "--lock accepts one package spec"
        raise PipxError(msg)
    if preinstall_packages:
        msg = "--lock cannot be combined with --preinstall"
        raise PipxError(msg)
    if upgrade:
        msg = "--lock cannot be combined with --upgrade; use --force to apply a new lock"
        raise PipxError(msg)
    if cooldown_days is not None:
        msg = "--lock cannot be combined with --cooldown"
        raise PipxError(msg)
    lock_file = lock_file.expanduser().resolve()
    if not _PYLOCK_NAME_RE.fullmatch(lock_file.name):
        msg = "Lock files must be named pylock.toml or pylock.<name>.toml"
        raise PipxError(msg)
    if not lock_file.is_file():
        msg = f"Lock file does not exist: {lock_file}"
        raise PipxError(msg)
    return lock_file


def _failed_install_result(environment: str, error: PipxError) -> OperationResult[InstallData]:
    return OperationResult(
        command=("install",),
        data=InstallData(packages=(), skipped=()),
        messages=(OutputMessage(str(error), stream=OutputStream.STDERR, level=OutputLevel.ERROR),),
        exit_code=ExitCode(1),
        errors=(
            OperationError(
                code="package_install_failed",
                message=_error_report(error),
                environment=redact_url_credentials(environment),
            ),
        ),
    )


def _record_install_failure(
    failures: list[_FailedInstall],
    messages: list[OutputMessage],
    environment: str,
    error: PipxError,
) -> None:
    failures.append(_FailedInstall(environment, _error_report(error)))
    messages.append(OutputMessage(str(error), stream=OutputStream.STDERR, level=OutputLevel.ERROR))


def _error_report(error: PipxError) -> str:
    # the envelope is all a JSON consumer reads, so it keeps the installer's reason the terminal showed beside it
    return f"{error}\n{error.backend_output}" if error.backend_output else str(error)


def _finish_install(result: OperationResult[InstallData], *, emit_output: bool) -> OperationResult[InstallData]:
    if not emit_output:
        return result
    if result.errors:
        render_messages(
            tuple(message for message in result.messages if message.level is OutputLevel.NORMAL),
            quiet=0,
        )
        raise PipxError(next(message.text for message in result.messages if message.level is OutputLevel.ERROR))
    render_result(result, output=OutputFormat.HUMAN, quiet=0)
    return result


def _first_cooldown(*candidates: int | None) -> int | None:
    return next((candidate for candidate in candidates if candidate is not None), None)


def _resolve_cooldown(
    lock_file: Path | None,
    requested: int | None,
    stored: int | None,
    *,
    modifies_existing: bool,
    env_cooldown_days: int | None = None,
) -> int | None:
    if modifies_existing and lock_file is not None and requested is not None:
        msg = "--cooldown cannot modify a locked environment"
        raise PipxError(msg)
    if lock_file is not None:
        return None
    # PIPX_COOLDOWN states a current machine-wide policy, so it outranks the cooldown the venv was last installed with
    return _first_cooldown(requested, env_cooldown_days, stored)


def _handle_existing_install(  # ruff:ignore[too-many-arguments]  # forwards the flat install context for an existing venv
    venv: Venv,
    package_name: str,
    package_spec: str,
    local_bin_dir: Path,
    local_man_dir: Path,
    *,
    python: str,
    pip_args: list[str],
    verbose: bool,
    force: bool,
    reinstall: bool,
    upgrade: bool,
    python_flag_passed: bool,
    upgrade_strategy: str | None,
    expected_apps: Sequence[str],
    cooldown_days: int | None,
) -> _ExistingInstall:
    messages: Final[list[OutputMessage]] = []
    if not reinstall and force and python_flag_passed:
        messages.append(
            OutputMessage(
                pipx_wrap(
                    f"""
                    --python is ignored when --force is passed.
                    If you want to reinstall {package_name} with {python},
                    run `pipx reinstall {venv.name} --python {python}` instead.
                    """
                )
            )
        )
    if force:
        messages.append(OutputMessage(f"Installing to existing venv {venv.name!r}"))
        return _ExistingInstall(
            continue_install=True,
            packages=(),
            skipped=(),
            messages=tuple(messages),
        )
    if upgrade:
        reason, upgrade_messages = _upgrade_existing_venv(
            venv,
            package_name,
            package_spec,
            local_bin_dir,
            local_man_dir,
            pip_args=pip_args,
            verbose=verbose,
            upgrade_strategy=upgrade_strategy,
            expected_apps=expected_apps,
            cooldown_days=cooldown_days,
        )
        messages.extend(upgrade_messages)
        return _ExistingInstall(
            continue_install=False,
            packages=(_installed_package(venv, package_name),) if reason is None else (),
            skipped=(_SkippedInstall(venv.name, package_name, reason),) if reason is not None else (),
            messages=tuple(messages),
        )

    installed_version = venv.pipx_metadata.main_package.package_version
    messages.append(
        OutputMessage(
            pipx_wrap(
                f"""
                {venv.name!r}{f" ({installed_version})" if installed_version else ""} already seems to be installed. Not
                modifying existing installation in '{venv.root}'.
                Pass '--force' to force installation, or use
                'pipx upgrade {venv.name}' to upgrade.
                """,
                keep_newlines=True,
            )
        )
    )
    return _ExistingInstall(
        continue_install=False,
        packages=(),
        skipped=(_SkippedInstall(venv.name, package_name, "already-installed"),),
        messages=tuple(messages),
    )


def _upgrade_existing_venv(  # ruff:ignore[too-many-arguments]  # forwards the flat upgrade context for one existing venv
    venv: Venv,
    package_name: str,
    package_spec: str,
    local_bin_dir: Path,
    local_man_dir: Path,
    *,
    pip_args: list[str],
    verbose: bool,
    upgrade_strategy: str | None,
    expected_apps: Sequence[str],
    cooldown_days: int | None,
) -> tuple[str | None, tuple[OutputMessage, ...]]:
    package_metadata = venv.pipx_metadata.main_package
    installed_version: Final[str] = package_metadata.package_version
    if package_metadata.lock_file is not None:
        validate_expected_apps(venv, package_name, expected_apps)
        _record_expected_apps(venv, expected_apps)
        return "locked", (OutputMessage(locked_package_message(venv.name)),)
    if package_spec_satisfied(
        package_spec,
        package_name,
        installed_version,
        package_metadata.package_or_url or package_name,
    ):
        validate_expected_apps(venv, package_name, expected_apps)
        _record_expected_apps(venv, expected_apps)
        return "already-satisfied", (
            OutputMessage(
                f"{package_name} {installed_version} already satisfies {redact_url_credentials(package_spec)}"
            ),
        )
    if package_metadata.pinned:
        validate_expected_apps(venv, package_name, expected_apps)
        _record_expected_apps(venv, expected_apps)
        return "pinned", (
            OutputMessage(f"Not upgrading pinned package {venv.name}. Run `pipx unpin {venv.name}` to unpin it."),
        )

    with preserve_venv(venv.root, enabled=bool(expected_apps)):
        main_pip_args: Final[list[str]] = pip_args or trusted_recorded_pip_args(package_metadata.pip_args, venv.root)
        venv.check_upgrade_shared_libs(pip_args=main_pip_args, verbose=verbose)
        venv.upgrade_packaging_libraries(main_pip_args)
        upgrade_only = [f"--upgrade-strategy={upgrade_strategy}"] if upgrade_strategy is not None else None
        previous_resource_paths: Final[set[Path]] = get_expected_venv_resource_paths(venv, local_bin_dir, local_man_dir)
        venv.upgrade_package(
            package_name,
            package_spec,
            main_pip_args,
            include_dependencies=package_metadata.include_dependencies,
            include_resources_from=package_metadata.include_resources_from,
            include_apps=package_metadata.include_apps,
            is_main_package=True,
            suffix=package_metadata.suffix,
            upgrade_only_pip_args=upgrade_only,
            expected_apps=expected_apps,
            cooldown_days=cooldown_days,
        )
        validate_expected_apps(venv, package_name, expected_apps)
        package_metadata = venv.pipx_metadata.main_package
        if venv.pipx_metadata.exposure_enabled:
            expose_package_resources(package_metadata, local_bin_dir, local_man_dir, force=False)
            remove_stale_venv_resources(previous_resource_paths, venv, local_bin_dir, local_man_dir)
    return None, (
        OutputMessage(
            pipx_wrap(
                f"""
                upgraded package {venv.name} from {installed_version} to
                {package_metadata.package_version} (location: {venv.root!s})
                """
            )
        ),
    )


def _record_expected_apps(venv: Venv, expected_apps: Sequence[str]) -> None:
    expected: Final[list[str]] = list(dict.fromkeys(expected_apps))
    if venv.pipx_metadata.main_package.expected_apps == expected:
        return
    venv.pipx_metadata.main_package = replace(venv.pipx_metadata.main_package, expected_apps=expected)
    venv.pipx_metadata.write()


def _installed_package(venv: Venv, package_name: str) -> _InstalledPackage:
    package: Final[PackageInfo] = venv.package_metadata[package_name]
    return _InstalledPackage(
        environment=venv.name,
        package=str(package.package),
        version=package.package_version,
        location=str(venv.root),
        interpreter=venv.pipx_metadata.python_version,
        backend=venv.pipx_metadata.backend,
    )


def install_all(  # ruff:ignore[too-many-arguments, too-many-positional-arguments]  # mirrors the CLI's flat install-all option set
    spec_metadata_file: Path,
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str | None,
    pip_args: list[str],
    venv_args: list[str],
    *,
    verbose: bool,
    force: bool,
    backend: str | None = None,
    env_backend: str | None = None,
    cooldown_days: int | None = None,
    python_flag_passed: bool = False,
) -> ExitCode:
    venvs_metadata: Final[list[PipxMetadata]] = []
    malformed: PipxError | None = None
    try:
        for venv_metadata in extract_venv_metadata(spec_metadata_file):
            venvs_metadata.append(venv_metadata)
    except PipxError as error:
        # installing one by one reached a malformed entry only after the entries before it, so install those first
        if not venvs_metadata:
            raise
        malformed = error
    venv_container: Final[VenvContainer] = VenvContainer(paths.ctx.venvs)
    with expose_shared_resources_in_order(venvs_metadata, local_bin_dir, local_man_dir):
        outcomes: Final[list[tuple[str, bool]]] = fan_out(
            [
                partial(
                    _install_spec_venv,
                    venv_container,
                    venv_metadata,
                    local_bin_dir=local_bin_dir,
                    local_man_dir=local_man_dir,
                    python=python,
                    pip_args=pip_args,
                    venv_args=venv_args,
                    verbose=verbose,
                    force=force,
                    backend=backend,
                    env_backend=env_backend,
                    cooldown_days=cooldown_days,
                    python_flag_passed=python_flag_passed,
                )
                for venv_metadata in venvs_metadata
            ],
            sequential=verbose,
        )
    if malformed is not None:
        raise malformed
    if not any(succeeded for _, succeeded in outcomes):
        print(  # ruff:ignore[print]  # user-facing CLI output
            f"No packages installed after running 'pipx install-all {spec_metadata_file}' {sleep}"
        )
    if failed := [environment for environment, succeeded in outcomes if not succeeded]:
        msg = f"The following package(s) failed to install: {', '.join(failed)}"
        raise PipxError(msg)
    return EXIT_CODE_OK


def _install_spec_venv(  # ruff:ignore[too-many-arguments]  # forwards the flat install-all option set for one venv
    venv_container: VenvContainer,
    venv_metadata: PipxMetadata,
    *,
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str | None,
    pip_args: list[str],
    venv_args: list[str],
    verbose: bool,
    force: bool,
    backend: str | None,
    env_backend: str | None,
    cooldown_days: int | None,
    python_flag_passed: bool,
) -> tuple[str, bool]:
    main_package: Final[PackageInfo] = venv_metadata.main_package
    venv_dir: Final[Path] = venv_container.get_venv_dir(f"{main_package.package}{main_package.suffix}")
    interpreter: Final[str | None] = (
        python if python_flag_passed else get_python_interpreter(venv_metadata.source_interpreter) or python
    )
    packages: Final[list[PackageInfo]] = [main_package, *venv_metadata.injected_packages.values()]
    try:
        package_pip_args: Final[list[list[str]]] = (
            [pip_args or trusted_recorded_pip_args(package.pip_args, venv_dir) for package in packages]
            if pip_args or backend in {None, venv_metadata.backend}
            else _translate_recorded_pip_args(venv_metadata, packages, backend)
        )
        with locked_in_order(venv_container.venv_lock(venv_dir)) as venv_lock:
            package_cooldown = _resolve_cooldown(
                main_package.lock_file,
                cooldown_days,
                main_package.cooldown_days,
                modifies_existing=False,
            )
            installed = install(
                venv_dir,
                None,
                [generate_package_spec(main_package)],
                local_bin_dir,
                local_man_dir,
                interpreter,
                package_pip_args[0],
                venv_args or venv_metadata.venv_args,
                verbose=verbose,
                force=force,
                reinstall=False,
                include_dependencies=main_package.include_dependencies,
                include_resources_from=main_package.include_resources_from,
                preinstall_packages=[],
                expected_apps=main_package.expected_apps,
                lock_file=main_package.lock_file,
                suffix=main_package.suffix,
                python_flag_passed=python_flag_passed,
                backend=backend or venv_metadata.backend,
                env_backend=env_backend,
                exposure_enabled=venv_metadata.exposure_enabled,
                replace_expected_apps=True,
                replace_lock=True,
                venv_lock=venv_lock,
                cooldown_days=package_cooldown,
                pinned=main_package.pinned,
            )
            # install left an existing environment alone, so its injected packages must not change it either
            for inject_package, inject_pip_args in (
                () if installed.data.skipped else zip(packages[1:], package_pip_args[1:], strict=True)
            ):
                inject(
                    venv_dir=venv_dir,
                    package_specs=[generate_package_spec(inject_package)],
                    requirement_files=[],
                    pip_args=inject_pip_args,
                    verbose=verbose,
                    include_apps=inject_package.include_apps,
                    include_dependencies=inject_package.include_dependencies,
                    include_resources_from=inject_package.include_resources_from,
                    force=force,
                    suffix=inject_package.suffix == main_package.suffix,
                    cooldown_days=(cooldown_days if cooldown_days is not None else inject_package.cooldown_days),
                    pinned=inject_package.pinned,
                )
    except PipxError as error:
        print(error, file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output
        return venv_dir.name, False
    return venv_dir.name, True


def _translate_recorded_pip_args(
    venv_metadata: PipxMetadata, packages: list[PackageInfo], backend: str
) -> list[list[str]]:
    # recorded pip args can hold options only the recording backend accepts, such as pip's --progress-bar
    environment: Final[str] = f"{venv_metadata.main_package.package}{venv_metadata.main_package.suffix}"
    translations: Final[list[tuple[list[str], list[str]]]] = [
        _translate_pip_args(trusted_recorded_pip_args(package.pip_args, venv_metadata.venv_dir), backend, environment)
        for package in packages
    ]
    if dropped := list(
        dict.fromkeys(" ".join(map(redact_url_credentials, other)) for _, other in translations if other)
    ):
        kept: Final[list[str]] = list(
            dict.fromkeys(
                " ".join(map(redact_url_credentials, translated)) for translated, _ in translations if translated
            )
        )
        _LOGGER.warning(
            "%s  Ignoring pip args recorded for the %s backend of %s: %s%s",
            hazard,
            venv_metadata.backend,
            environment,
            " ".join(dropped),
            f"; translated for {backend}: {' '.join(kept)}" if kept else "",
        )
    return [translated for translated, _ in translations]


def _translate_pip_args(pip_args: list[str], backend: str, environment: str) -> tuple[list[str], list[str]]:
    # keeping the recorded index stops a snapshot moved to the other backend from installing from PyPI instead
    to_pip: Final[bool] = backend == PIP
    translated: Final[list[str]] = []
    dropped: Final[list[str]] = []
    arguments: Final[Iterator[str]] = iter(pip_args)
    for argument in arguments:
        flag, value = _split_option(argument if to_pip else _expand_pip_abbreviation(argument), arguments)
        spelling = _VALUE_OPTION_SPELLINGS.get(flag, (flag, flag))
        match spelling[0]:
            case "--no-index":
                translated.append(flag)
            case "--pre" | "--prerelease" if flag == "--pre" or value == "allow":
                translated.extend(["--pre"] if to_pip else ["--prerelease", "allow"])
            case "--prerelease":
                dropped.extend([flag, value])
            case "--index":
                # uv takes a named index as name=url, and the name means nothing to pip
                name, _, url = value.partition("=")
                translated.extend([spelling[to_pip], url if url and re.fullmatch(r"[A-Za-z0-9._-]+", name) else value])
            case "--find-links":
                # uv splits a --find-links value on commas, pip takes it as one location
                translated.extend(
                    part for link in (value.split(",") if to_pip else [value]) for part in (spelling[to_pip], link)
                )
            case "--default-index" | "--constraints":
                translated.extend([spelling[to_pip], value])
            case "--allow-insecure-host" if "://" not in value:
                translated.extend([spelling[to_pip], value])
            case "--keyring-provider" if value in {"disabled", "subprocess"}:
                translated.extend([flag, value])
            case "--index-strategy" if value == "unsafe-best-match":
                pass  # pip always picks the best match across its indexes
            case "--allow-insecure-host" | "--keyring-provider" | "--index-strategy":
                msg = (
                    f"Cannot install {environment} with the {backend} backend: its recorded index option {flag} "
                    f"{redact_url_credentials(value)} has no {backend} equivalent, and dropping it could install from "
                    "a different index."
                )
                raise PipxError(msg)
            case _:
                dropped.append(argument)
    return translated, dropped


def _expand_pip_abbreviation(argument: str) -> str:
    # pip accepts any unambiguous prefix of a long option, so a pip recording can hold --index-u for --index-url
    long_options: Final[tuple[str, ...]] = (
        "--index-url",
        "--extra-index-url",
        "--find-links",
        "--no-index",
        "--pre",
        "--trusted-host",
        "--constraint",
        "--keyring-provider",
    )
    flag, separator, value = argument.partition("=")
    if not flag.startswith("--") or flag in long_options:
        return argument
    matches: Final[list[str]] = [option for option in long_options if option.startswith(flag)]
    return f"{matches[0]}{separator}{value}" if len(matches) == 1 else argument


def _split_option(argument: str, arguments: Iterator[str]) -> tuple[str, str]:
    flag, _, value = argument.partition("=") if argument.startswith("--") else (argument[:2], "", argument[2:])
    if flag not in _VALUE_OPTION_SPELLINGS:
        return argument, ""
    return flag, value or next(arguments, "")


def extract_venv_metadata(spec_metadata_file: Path) -> Iterator[PipxMetadata]:
    try:
        spec: Final = load_spec_file(spec_metadata_file)
    except OSError as exc:
        msg = f"Unable to read the spec metadata file {spec_metadata_file}: {exc.strerror}"
        raise PipxError(msg) from exc
    except (json.decoder.JSONDecodeError, UnicodeDecodeError) as exc:
        msg = f"The spec metadata file {spec_metadata_file} is not valid JSON."
        raise PipxError(msg) from exc

    if not isinstance(spec, dict) or not isinstance(venvs_metadata_dict := spec.get("venvs", {}), dict):
        msg = f"The spec metadata file {spec_metadata_file} is invalid."
        raise PipxError(msg)
    if not venvs_metadata_dict:
        msg = f"No packages found in the spec metadata file {spec_metadata_file}."
        raise PipxError(msg)

    for package_path_name, entry in venvs_metadata_dict.items():
        venv_dir = paths.ctx.venvs.joinpath(package_path_name)
        venv_metadata = PipxMetadata(venv_dir, read=False)
        try:
            venv_metadata.from_dict(entry["metadata"])
        except KeyError as exc:
            msg = f"Entry {package_path_name!r} in the spec metadata file {spec_metadata_file} is missing {exc}."
            raise PipxError(msg) from exc
        except (AttributeError, TypeError) as exc:
            msg = f"Entry {package_path_name!r} in the spec metadata file {spec_metadata_file} is malformed: {exc}"
            raise PipxError(msg) from exc
        yield venv_metadata


def generate_package_spec(package_info: PackageInfo) -> str:
    """Generate more precise package spec from package info."""
    if not package_info.package_or_url:
        msg = f"A package spec is not available for {package_info.package}"
        raise PipxError(msg)

    if package_info.package == package_info.package_or_url:
        return f"{package_info.package}=={package_info.package_version}"
    return package_info.package_or_url


def get_python_interpreter(
    source_interpreter: Path | None,
) -> str | None:
    """Get appropriate python interpreter."""
    if source_interpreter is None:
        return None
    if source_interpreter.is_file():
        return str(source_interpreter)

    print(  # ruff:ignore[print]  # user-facing CLI output
        pipx_wrap(
            f"""
            The exported python interpreter '{source_interpreter}' is ignored
            as not found.
            """
        )
    )

    return None


@dataclass(frozen=True)
class _InstalledPackage:
    environment: str
    package: str
    version: str
    location: str
    interpreter: str | None
    backend: str


@dataclass(frozen=True)
class _SkippedInstall:
    environment: str
    package: str
    reason: str


@dataclass(frozen=True)
class _FailedInstall:
    environment: str
    error: str


@dataclass(frozen=True)
class _ExistingInstall:
    continue_install: bool
    packages: tuple[_InstalledPackage, ...]
    skipped: tuple[_SkippedInstall, ...]
    messages: tuple[OutputMessage, ...]


@dataclass(frozen=True)
class InstallData(OperationData):
    packages: tuple[_InstalledPackage, ...]
    skipped: tuple[_SkippedInstall, ...]


@dataclass(frozen=True)
class _EnvironmentBuild:
    """Everything needed to fill a venv, so pipx can do it twice when the first interpreter turns out unsupported."""

    venv_args: list[str]
    pip_args: list[str]
    override_shared: bool
    exposure_enabled: bool
    preinstall_packages: list[str] | None
    package_name: str
    package_spec: str
    force_reinstall: bool
    include_dependencies: bool
    include_resources_from: Sequence[str]
    suffix: str
    expected_apps: tuple[str, ...]
    lock_file: Path | None
    cooldown_days: int | None
    pinned: bool

    def run(self, venv: Venv) -> VenvMetadata:
        venv.create_venv(self.venv_args, self.pip_args, override_shared=self.override_shared)
        venv.pipx_metadata.exposure_enabled = self.exposure_enabled
        venv.pipx_metadata.environment = venv.root.name
        # the record is written last, so a kill before it must not leave what looks like a pre-0.15 environment
        with marked_unfinished(venv.root):
            for dependency in self.preinstall_packages or []:
                venv.upgrade_package_no_metadata(dependency, self.pip_args, cooldown_days=self.cooldown_days)
            return venv.install_package(
                package_name=self.package_name,
                package_or_url=self.package_spec,
                pip_args=self.pip_args,
                install_only_pip_args=["--force-reinstall"] if self.force_reinstall else None,
                include_dependencies=self.include_dependencies,
                include_resources_from=self.include_resources_from,
                include_apps=True,
                is_main_package=True,
                suffix=self.suffix,
                expected_apps=self.expected_apps,
                lock_file=self.lock_file,
                cooldown_days=self.cooldown_days,
                pinned=self.pinned,
            )


def _install_on_supported_python(  # ruff:ignore[too-many-arguments]  # forwards the flat rebuild context around the interpreter retry
    venv: Venv,
    build: _EnvironmentBuild,
    *,
    venv_dir: Path,
    venv_backup: VenvBackup,
    fetch_python: FetchPythonOptions,
    python_flag_passed: bool,
    verbose: bool,
    messages: list[OutputMessage],
) -> Venv:
    try:
        # uv installs onto an interpreter above the package's upper bound, so ask the metadata as well
        constraint = build.run(venv).unsupported_python
    except IncompatiblePythonError as error:
        constraint = error.constraint
    if constraint is None:
        return venv

    venv = _rebuild_on_supported_python(
        venv_dir=venv_dir,
        venv_backup=venv_backup,
        constraint=constraint,
        fetch_python=fetch_python,
        python_flag_passed=python_flag_passed,
        verbose=verbose,
        # the rebuild deletes the recorded backend; resolving it again could switch installer and index
        backend=venv.backend_name,
        messages=messages,
    )
    build.run(venv)
    return venv


def _supported_python(
    constraint: SpecifierSet,
    *,
    fetch_python: FetchPythonOptions,
    python_flag_passed: bool,
    messages: list[OutputMessage],
) -> str:
    if python_flag_passed:
        msg = (
            f"The Python you named does not satisfy {str(constraint)!r}, which this package requires. "
            f"Name one that does, or leave --python out and let pipx choose."
        )
        raise PipxError(msg)
    interpreter: Final[str] = interpreter_for(constraint, fetch_python)
    messages.append(OutputMessage(f"This package needs Python {constraint}, so pipx used {interpreter}.", notice=True))
    return interpreter


def _rebuild_on_supported_python(  # ruff:ignore[too-many-arguments]  # forwards the flat rebuild context to a fresh venv
    *,
    venv_dir: Path,
    venv_backup: VenvBackup,
    constraint: SpecifierSet,
    fetch_python: FetchPythonOptions,
    python_flag_passed: bool,
    verbose: bool,
    backend: str,
    messages: list[OutputMessage],
) -> Venv:
    interpreter: Final[str] = _supported_python(
        constraint,
        fetch_python=fetch_python,
        python_flag_passed=python_flag_passed,
        messages=messages,
    )
    venv_backup.remove_venv()
    return Venv(venv_dir, python=interpreter, verbose=verbose, backend=backend)


__all__ = [
    "InstallData",
    "extract_venv_metadata",
    "generate_package_spec",
    "get_python_interpreter",
    "install",
    "install_all",
]
