from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final

from packaging.utils import canonicalize_name

from pipx import commands, paths
from pipx.backends import PIP
from pipx.commands.common import (
    expose_package_resources,
    get_expected_venv_resource_paths,
    locked_package_message,
    package_name_from_spec,
    run_post_install_actions,
    validate_expected_apps,
)
from pipx.commands.transaction import preserve_venv
from pipx.constants import (
    EXIT_CODE_OK,
    ExitCode,
)
from pipx.emojis import sleep
from pipx.interpreter import get_default_python
from pipx.package_specifier import package_spec_satisfied
from pipx.pipx_metadata_file import PackageInfo, PipxMetadata, load_spec_file
from pipx.result import (
    OperationData,
    OperationResult,
    OutputFormat,
    OutputLevel,
    OutputMessage,
    OutputStream,
    render_messages,
    render_result,
)
from pipx.util import PipxError, pipx_wrap, rmdir
from pipx.venv import Venv, VenvContainer

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path

    from filelock import BaseFileLock

_PYLOCK_NAME_RE: Final[re.Pattern[str]] = re.compile(r"pylock(?:\.[^.]+)?\.toml")


def install(
    venv_dir: Path | None,
    package_names: list[str] | None,
    package_specs: list[str],
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str | None,
    pip_args: list[str],
    venv_args: list[str],
    verbose: bool,
    *,
    force: bool,
    reinstall: bool,
    include_dependencies: bool,
    include_apps_from: Sequence[str],
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
    venv_lock: BaseFileLock | None = None,
    preserve_existing: bool = False,
    replace_expected_apps: bool = False,
    replace_lock: bool = False,
    emit_output: bool = True,
) -> OperationResult[InstallData]:
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

    package_names, resolution_failure = _resolve_package_names(
        package_names,
        package_specs,
        python,
        pip_args,
        verbose,
        backend=backend,
        env_backend=env_backend,
        cooldown_days=cooldown_days,
    )
    if resolution_failure is not None:
        package_spec, resolution_error = resolution_failure
        return _finish_install(_failed_install_result(package_spec, resolution_error), emit_output=emit_output)

    venv_container: Final[VenvContainer] = VenvContainer(venv_dir.parent if venv_dir is not None else paths.ctx.venvs)
    for package_name, package_spec in zip(package_names, package_specs, strict=False):
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

            try:
                venv = Venv(
                    venv_dir,
                    python=python,
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
                )
                required_exposure = venv.pipx_metadata.exposure_enabled if exposure_enabled is None else exposure_enabled
                if exists:
                    existing = _handle_existing_install(
                        venv,
                        package_name,
                        package_spec,
                        local_bin_dir,
                        local_man_dir,
                        python,
                        pip_args,
                        verbose,
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
            except PipxError as error:
                _record_install_failure(failures, messages, environment, error)
                break

            previous_resource_paths: set[Path] = get_expected_venv_resource_paths(venv, local_bin_dir, local_man_dir)
            preserve_existing_venv = exists and (
                preserve_existing or bool(required_apps or include_apps_from) or required_lock is not None
            )
            try:
                with preserve_venv(venv_dir, enabled=preserve_existing_venv):
                    venv.check_upgrade_shared_libs(pip_args=pip_args, verbose=verbose)
                    if exists and (required_lock is not None or (replace_lock and recorded_lock is not None)):
                        recorded_backend = venv.pipx_metadata.backend
                        rmdir(venv_dir)
                        venv = Venv(
                            venv_dir,
                            python=python,
                            verbose=verbose,
                            backend=install_backend or recorded_backend,
                        )
                    override_shared = canonicalize_name(package_name) == "pip"
                    venv.create_venv(venv_args, pip_args, override_shared)
                    venv.pipx_metadata.exposure_enabled = required_exposure
                    venv.pipx_metadata.environment = venv.root.name
                    for dependency in preinstall_packages or []:
                        venv.upgrade_package_no_metadata(dependency, pip_args, cooldown_days=required_cooldown)
                    venv.install_package(
                        package_name=package_name,
                        package_or_url=package_spec,
                        pip_args=pip_args,
                        install_only_pip_args=["--force-reinstall"] if force and exists else None,
                        include_dependencies=include_dependencies,
                        include_apps_from=include_apps_from,
                        include_apps=True,
                        is_main_package=True,
                        suffix=suffix,
                        expected_apps=required_apps,
                        lock_file=required_lock,
                        cooldown_days=required_cooldown,
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
                if not preserve_existing_venv:
                    venv.remove_venv()
                if not isinstance(error, PipxError):
                    raise
                _record_install_failure(failures, messages, venv.name, error)
                break
            packages.append(_installed_package(venv, package_name))
        venv_dir = None

    return _finish_install(
        OperationResult(
            command="install",
            data=InstallData(packages=tuple(packages), skipped=tuple(skipped), failures=tuple(failures)),
            messages=tuple(messages),
            exit_code=ExitCode(1 if failures else 0),
        ),
        emit_output=emit_output,
    )


def _prepare_install(
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


def _resolve_package_names(
    package_names: list[str] | None,
    package_specs: list[str],
    python: str,
    pip_args: list[str],
    verbose: bool,
    *,
    backend: str | None,
    env_backend: str | None,
    cooldown_days: int | None,
) -> tuple[list[str], tuple[str, PipxError] | None]:
    if package_names is not None and len(package_names) == len(package_specs):
        return package_names, None

    resolved: Final[list[str]] = []
    for package_spec in package_specs:
        try:
            resolved.append(
                package_name_from_spec(
                    package_spec,
                    python,
                    pip_args=pip_args,
                    verbose=verbose,
                    backend=backend,
                    env_backend=env_backend,
                    cooldown_days=cooldown_days,
                )
            )
        except PipxError as error:
            return resolved, (package_spec, error)
    return resolved, None


def _validate_install_options(
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
        raise PipxError("--upgrade-strategy requires --upgrade")
    if expected_apps and len(package_specs) != 1:
        raise PipxError("--app accepts one package spec")
    if lock_file is None:
        return None
    if len(package_specs) != 1:
        raise PipxError("--lock accepts one package spec")
    if preinstall_packages:
        raise PipxError("--lock cannot be combined with --preinstall")
    if upgrade:
        raise PipxError("--lock cannot be combined with --upgrade; use --force to apply a new lock")
    if cooldown_days is not None:
        raise PipxError("--lock cannot be combined with --cooldown")
    lock_file = lock_file.expanduser().resolve()
    if not _PYLOCK_NAME_RE.fullmatch(lock_file.name):
        raise PipxError("Lock files must be named pylock.toml or pylock.<name>.toml")
    if not lock_file.is_file():
        raise PipxError(f"Lock file does not exist: {lock_file}")
    return lock_file


def _failed_install_result(environment: str, error: PipxError) -> OperationResult[InstallData]:
    message: Final[str] = str(error)
    return OperationResult(
        command="install",
        data=InstallData(packages=(), skipped=(), failures=(_FailedInstall(environment, message),)),
        messages=(OutputMessage(message, stream=OutputStream.STDERR, level=OutputLevel.ERROR),),
        exit_code=ExitCode(1),
    )


def _record_install_failure(
    failures: list[_FailedInstall],
    messages: list[OutputMessage],
    environment: str,
    error: PipxError,
) -> None:
    failures.append(_FailedInstall(environment, str(error)))
    messages.append(OutputMessage(str(error), stream=OutputStream.STDERR, level=OutputLevel.ERROR))


def _finish_install(result: OperationResult[InstallData], *, emit_output: bool) -> OperationResult[InstallData]:
    if not emit_output:
        return result
    if result.data.failures:
        render_messages(
            tuple(message for message in result.messages if message.level is OutputLevel.NORMAL),
            quiet=0,
        )
        raise PipxError(result.data.failures[0].error)
    render_result(result, output=OutputFormat.HUMAN, quiet=0)
    return result


def _resolve_cooldown(
    lock_file: Path | None,
    requested: int | None,
    stored: int | None,
    *,
    modifies_existing: bool,
) -> int | None:
    if modifies_existing and lock_file is not None and requested is not None:
        raise PipxError("--cooldown cannot modify a locked environment")
    if lock_file is not None:
        return None
    return requested if requested is not None else stored


def _handle_existing_install(
    venv: Venv,
    package_name: str,
    package_spec: str,
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str,
    pip_args: list[str],
    verbose: bool,
    *,
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
                    run `pipx reinstall {package_spec} --python {python}` instead.
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
            pip_args,
            verbose,
            upgrade_strategy,
            expected_apps,
            cooldown_days,
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


def _upgrade_existing_venv(
    venv: Venv,
    package_name: str,
    package_spec: str,
    local_bin_dir: Path,
    local_man_dir: Path,
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
            OutputMessage(f"{package_name} {installed_version} already satisfies {package_spec}"),
        )
    if package_metadata.pinned:
        validate_expected_apps(venv, package_name, expected_apps)
        _record_expected_apps(venv, expected_apps)
        return "pinned", (
            OutputMessage(f"Not upgrading pinned package {venv.name}. Run `pipx unpin {venv.name}` to unpin it."),
        )

    with preserve_venv(venv.root, enabled=bool(expected_apps)):
        main_pip_args: Final[list[str]] = pip_args or package_metadata.pip_args
        venv.check_upgrade_shared_libs(pip_args=main_pip_args, verbose=verbose)
        venv.upgrade_packaging_libraries(main_pip_args)
        venv.upgrade_package(
            package_name,
            package_spec,
            main_pip_args,
            include_dependencies=package_metadata.include_dependencies,
            include_apps_from=package_metadata.include_apps_from,
            include_apps=package_metadata.include_apps,
            is_main_package=True,
            suffix=package_metadata.suffix,
            upgrade_only_pip_args=([f"--upgrade-strategy={upgrade_strategy}"] if upgrade_strategy is not None else None),
            expected_apps=expected_apps,
            cooldown_days=cooldown_days,
        )
        validate_expected_apps(venv, package_name, expected_apps)
        package_metadata = venv.pipx_metadata.main_package
        if venv.pipx_metadata.exposure_enabled:
            expose_package_resources(package_metadata, local_bin_dir, local_man_dir, force=False)
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
    )


def install_all(
    spec_metadata_file: Path,
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str | None,
    pip_args: list[str],
    venv_args: list[str],
    verbose: bool,
    *,
    force: bool,
    backend: str | None = None,
    env_backend: str | None = None,
    cooldown_days: int | None = None,
) -> ExitCode:
    venv_container: Final[VenvContainer] = VenvContainer(paths.ctx.venvs)
    failed: Final[list[str]] = []
    installed: Final[list[str]] = []

    for venv_metadata in extract_venv_metadata(spec_metadata_file):
        main_package = venv_metadata.main_package
        venv_dir = venv_container.get_venv_dir(f"{main_package.package}{main_package.suffix}")
        try:
            with venv_container.venv_lock(venv_dir) as venv_lock:
                package_cooldown = _resolve_cooldown(
                    main_package.lock_file,
                    cooldown_days,
                    main_package.cooldown_days,
                    modifies_existing=False,
                )
                install(
                    venv_dir,
                    None,
                    [generate_package_spec(main_package)],
                    local_bin_dir,
                    local_man_dir,
                    python or get_python_interpreter(venv_metadata.source_interpreter),
                    pip_args,
                    venv_args,
                    verbose,
                    force=force,
                    reinstall=False,
                    include_dependencies=main_package.include_dependencies,
                    include_apps_from=main_package.include_apps_from,
                    preinstall_packages=[],
                    expected_apps=main_package.expected_apps,
                    lock_file=main_package.lock_file,
                    suffix=main_package.suffix,
                    backend=backend or venv_metadata.backend,
                    env_backend=env_backend,
                    exposure_enabled=venv_metadata.exposure_enabled,
                    replace_expected_apps=True,
                    replace_lock=True,
                    venv_lock=venv_lock,
                    cooldown_days=package_cooldown,
                )
                for inject_package in venv_metadata.injected_packages.values():
                    commands.inject(
                        venv_dir=venv_dir,
                        package_specs=[generate_package_spec(inject_package)],
                        requirement_files=[],
                        pip_args=pip_args,
                        verbose=verbose,
                        include_apps=inject_package.include_apps,
                        include_dependencies=inject_package.include_dependencies,
                        include_apps_from=inject_package.include_apps_from,
                        force=force,
                        suffix=inject_package.suffix == main_package.suffix,
                        cooldown_days=(cooldown_days if cooldown_days is not None else inject_package.cooldown_days),
                    )
        except PipxError as error:
            print(error, file=sys.stderr)
            failed.append(venv_dir.name)
        else:
            installed.append(venv_dir.name)
    if not installed:
        print(f"No packages installed after running 'pipx install-all {spec_metadata_file}' {sleep}")
    if failed:
        raise PipxError(f"The following package(s) failed to install: {', '.join(failed)}")
    return EXIT_CODE_OK


def extract_venv_metadata(spec_metadata_file: Path) -> Iterator[PipxMetadata]:
    try:
        spec: Final = load_spec_file(spec_metadata_file)
    except json.decoder.JSONDecodeError as exc:
        raise PipxError("The spec metadata file is an invalid JSON file.") from exc

    venvs_metadata_dict: Final = spec.get("venvs")
    if not venvs_metadata_dict:
        raise PipxError("No packages found in the spec metadata file.")
    if not isinstance(venvs_metadata_dict, dict):
        raise PipxError("The spec metadata file is invalid.")

    for package_path_name, entry in venvs_metadata_dict.items():
        venv_dir = paths.ctx.venvs.joinpath(package_path_name)
        venv_metadata = PipxMetadata(venv_dir, read=False)
        venv_metadata.from_dict(entry["metadata"])
        yield venv_metadata


def generate_package_spec(package_info: PackageInfo) -> str:
    """Generate more precise package spec from package info."""
    if not package_info.package_or_url:
        raise PipxError(f"A package spec is not available for {package_info.package}")

    if package_info.package == package_info.package_or_url:
        return f"{package_info.package}=={package_info.package_version}"
    return package_info.package_or_url


def get_python_interpreter(
    source_interpreter: Path | None,
) -> str | None:
    """Get appropriate python interpreter."""
    if source_interpreter is not None and source_interpreter.is_file():
        return str(source_interpreter)

    print(
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
    failures: tuple[_FailedInstall, ...]


__all__ = [
    "InstallData",
    "extract_venv_metadata",
    "generate_package_spec",
    "get_python_interpreter",
    "install",
    "install_all",
]
