from __future__ import annotations

__lazy_modules__ = [
    "functools",
    "json",
    "packaging.utils",
    "pipx",
    "pipx.backends._base",
    "pipx.commands.common",
    "pipx.commands.inject",
    "pipx.commands.transaction",
    "pipx.fanout",
    "pipx.interpreter",
    "pipx.options",
    "pipx.package_specifier",
    "pipx.pipx_metadata_file",
    "pipx.redact",
    "pipx.requires_python",
    "pipx.script",
    "pipx.trash",
    "pipx.util",
    "pipx.venv",
    "pipx.wrap",
    "re",
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
from pipx.backends._base import PIP
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
from pipx.constants import EXIT_CODE_OK, ExitCode
from pipx.emojis import HAZARD, SLEEP
from pipx.fanout import fan_out, locked_in_order
from pipx.interpreter import get_default_python
from pipx.options import BackendOptions, CooldownOptions, ExposureOptions, InjectOptions, InstallOptions
from pipx.package_specifier import (
    changeable_by_others,
    package_spec_satisfied,
    translate_pip_args,
    trusted_recorded_pip_args,
)
from pipx.pipx_metadata_file import PackageInfo, PipxMetadata, load_spec_file
from pipx.redact import redact_url_credentials
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
from pipx.trash import rmdir
from pipx.util import PipxError
from pipx.venv import Venv, VenvContainer
from pipx.wrap import pipx_wrap

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path

    from filelock import BaseFileLock
    from packaging.specifiers import SpecifierSet

    from pipx.constants import FetchPythonOptions
    from pipx.venv_inspect import VenvMetadata

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def install(  # ruff:ignore[too-many-locals, too-many-statements]  # one pass resolves, builds and exposes each venv under its lock
    venv_dir: Path | None,
    package_names: list[str] | None,
    package_specs: list[str],
    options: InstallOptions,
    *,
    venv_lock: BaseFileLock | None = None,
) -> OperationResult[InstallData]:
    validate_suffix(options.exposure.suffix)
    messages: Final[list[OutputMessage]] = []
    packages: Final[list[_InstalledPackage]] = []
    skipped: Final[list[_SkippedInstall]] = []
    failures: Final[list[_FailedInstall]] = []
    try:
        lock_file: Final[Path | None] = _validate_install_options(package_specs, options)
        python: Final[str] = options.python or get_default_python()
    except PipxError as error:
        return _finish_install(_failed_install_result(package_specs[0], error), emit_output=options.emit_output)

    package_names, resolution_failure, interpreters = _resolve_package_names(
        package_names, package_specs, python, options, messages=messages
    )
    if resolution_failure is not None:
        package_spec, resolution_error = resolution_failure
        return _finish_install(_failed_install_result(package_spec, resolution_error), emit_output=options.emit_output)

    venv_container: Final[VenvContainer] = VenvContainer(venv_dir.parent if venv_dir is not None else paths.CTX.venvs)
    for package_name, package_spec, package_python in zip(package_names, package_specs, interpreters, strict=False):
        if venv_dir is None:
            venv_dir = venv_container.get_venv_dir(f"{package_name}{options.exposure.suffix}")

        with venv_lock or venv_container.venv_lock(venv_dir):
            exists: Final[bool] = venv_dir.exists() and any(venv_dir.iterdir())
            installs_pip: Final[bool] = canonicalize_name(package_name) == "pip"
            try:  # ruff:ignore[too-many-statements-in-try-clause]  # one PipxError handler must cover the whole existing-venv resolution
                venv = Venv(
                    venv_dir,
                    python=package_python,
                    verbose=options.verbose,
                    # `pipx install pip` needs pip, which uv venvs lack; an explicit --backend uv still reaches
                    # assert_not_pip_under_uv and fails
                    backend=BackendOptions(cli=options.backend.cli or PIP) if installs_pip else options.backend,
                )
                recorded_lock: Final[Path | None] = venv.pipx_metadata.main_package.lock_file
                required_lock: Final[Path | None] = lock_file if options.replace_lock else lock_file or recorded_lock
                build: Final[_EnvironmentBuild] = _EnvironmentBuild(
                    venv_args=options.venv_args,
                    pip_args=options.pip_args,
                    override_shared=installs_pip,
                    exposure_enabled=venv.pipx_metadata.exposure_enabled
                    if options.exposure_enabled is None
                    else options.exposure_enabled,
                    preinstall_packages=options.preinstall_packages,
                    package_name=package_name,
                    package_spec=package_spec,
                    force_reinstall=options.force and exists,
                    exposure=options.exposure,
                    expected_apps=tuple(
                        dict.fromkeys(
                            options.expected_apps
                            if options.replace_expected_apps
                            else options.expected_apps or venv.pipx_metadata.main_package.expected_apps
                        )
                    ),
                    lock_file=required_lock,
                    cooldown_days=_resolve_cooldown(
                        required_lock,
                        options.cooldown,
                        venv.pipx_metadata.main_package.cooldown_days,
                        modifies_existing=exists and options.force,
                    ),
                    pinned=venv.pipx_metadata.main_package.pinned if options.pinned is None else options.pinned,
                )
                if exists:
                    existing: Final[_ExistingInstall] = _handle_existing_install(
                        venv, build, options, python=package_python
                    )
                    messages.extend(existing.messages)
                    packages.extend(existing.packages)
                    skipped.extend(existing.skipped)
                    if not existing.continue_install:
                        venv_dir = None
                        continue
                    # --force reuses the environment, so --python does not switch it; `pipx reinstall --python` does
                    if (
                        options.python_flag_passed
                        and (recorded := venv.pipx_metadata.source_interpreter) is not None
                        and recorded.is_file()
                    ):
                        venv.python = str(recorded)
            except PipxError as error:
                _record_install_failure(failures, messages, venv_dir.name, error)
                break

            previous_resource_paths: Final[set[Path]] = get_expected_venv_resource_paths(
                venv, options.local_bin_dir, options.local_man_dir
            )
            preserve_existing_venv: Final[bool] = exists and (
                options.preserve_existing
                or bool(build.expected_apps or options.exposure.include_resources_from)
                or required_lock is not None
            )
            try:  # ruff:ignore[too-many-statements-in-try-clause]  # one handler must roll back the whole build-and-expose sequence on failure
                with preserve_venv(venv_dir, enabled=exists, copy_upfront=preserve_existing_venv) as venv_backup:
                    venv.check_upgrade_shared_libs(pip_args=options.pip_args, verbose=options.verbose)
                    if exists and (required_lock is not None or (options.replace_lock and recorded_lock is not None)):
                        rmdir(venv_dir)
                        venv = Venv(
                            venv_dir,
                            python=venv.python,
                            verbose=options.verbose,
                            backend=BackendOptions(cli=venv.backend_name),
                        )
                    venv = _install_on_supported_python(
                        venv, build, options, venv_backup=venv_backup, messages=messages
                    )
                    validate_expected_apps(venv, package_name, build.expected_apps)
                    messages.extend(
                        run_post_install_actions(
                            venv,
                            package_name,
                            options.local_bin_dir,
                            options.local_man_dir,
                            venv_dir,
                            force=options.force,
                            previous_resource_paths=previous_resource_paths,
                        )
                    )
            except (Exception, KeyboardInterrupt) as error:
                # any failure, an interrupt included, rolls back a new environment; pipx reports only a PipxError
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
        emit_output=options.emit_output,
    )


def _validate_install_options(package_specs: Sequence[str], options: InstallOptions) -> Path | None:
    if options.upgrade_strategy is not None and not options.upgrade:
        msg = "--upgrade-strategy requires --upgrade"
        raise PipxError(msg)
    if options.expected_apps and len(package_specs) != 1:
        msg = "--app accepts one package spec"
        raise PipxError(msg)
    if options.lock_file is None:
        return None
    if len(package_specs) != 1:
        msg = "--lock accepts one package spec"
        raise PipxError(msg)
    if options.preinstall_packages:
        msg = "--lock cannot be combined with --preinstall"
        raise PipxError(msg)
    if options.upgrade:
        msg = "--lock cannot be combined with --upgrade; use --force to apply a new lock"
        raise PipxError(msg)
    if options.cooldown.cli_days is not None:
        msg = "--lock cannot be combined with --cooldown"
        raise PipxError(msg)
    lock_file: Final[Path] = options.lock_file.expanduser().resolve()
    if not re.fullmatch(r"pylock(?:\.[^.]+)?\.toml", lock_file.name):
        msg = f"Rename the lock file {lock_file.name!r} to pylock.toml or pylock.<name>.toml"
        raise PipxError(msg)
    if not lock_file.is_file():
        msg = f"Lock file does not exist: {lock_file}"
        raise PipxError(msg)
    return lock_file


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


def _failed_install_result(environment: str, error: PipxError) -> OperationResult[InstallData]:
    return OperationResult(
        command=("install",),
        data=InstallData(packages=(), skipped=()),
        messages=(OutputMessage(text=str(error), stream=OutputStream.STDERR, level=OutputLevel.ERROR),),
        exit_code=ExitCode(1),
        errors=(
            OperationError(
                code="package_install_failed",
                message=_error_report(error),
                environment=redact_url_credentials(environment),
            ),
        ),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class InstallData(OperationData):
    packages: tuple[_InstalledPackage, ...]
    skipped: tuple[_SkippedInstall, ...]


def _error_report(error: PipxError) -> str:
    # a JSON consumer reads only the envelope, which needs the installer's reason the terminal showed beside it
    return f"{error}\n{error.backend_output}" if error.backend_output else str(error)


def _first_cooldown(*candidates: int | None) -> int | None:
    return next((candidate for candidate in candidates if candidate is not None), None)


def _resolve_package_names(
    package_names: list[str] | None,
    package_specs: list[str],
    python: str,
    options: InstallOptions,
    *,
    messages: list[OutputMessage],
) -> tuple[list[str], tuple[str, PipxError] | None, list[str]]:
    if package_names is not None and len(package_names) == len(package_specs):
        return package_names, None, [python] * len(package_specs)

    # a lock file already pins every version, leaving PIPX_COOLDOWN nothing to constrain
    cooldown_days: Final[int | None] = None if options.lock_file is not None else options.cooldown.days
    expected_apps: Final[tuple[str, ...]] = tuple(options.expected_apps)
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
                    pip_args=options.pip_args,
                    verbose=options.verbose,
                    backend=options.backend,
                    cooldown_days=cooldown_days,
                )
            except IncompatiblePythonError as error:
                # reading the name off a local project already runs an install, so the constraint surfaces here first
                interpreter = _supported_python(
                    error.constraint,
                    fetch_python=options.fetch_python,
                    python_flag_passed=options.python_flag_passed,
                    messages=messages,
                )
                name = package_name_from_spec(
                    package_spec,
                    interpreter,
                    pip_args=options.pip_args,
                    verbose=options.verbose,
                    backend=options.backend,
                    cooldown_days=cooldown_days,
                )
            resolved.append(name)
            interpreters.append(interpreter)
        except PipxError as error:
            return resolved, (package_spec, error), interpreters
    return resolved, None, interpreters


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
    messages.append(
        OutputMessage(text=f"This package needs Python {constraint}, so pipx used {interpreter}.", notice=True)
    )
    return interpreter


def _resolve_cooldown(
    lock_file: Path | None,
    requested: CooldownOptions,
    stored: int | None,
    *,
    modifies_existing: bool,
) -> int | None:
    if modifies_existing and lock_file is not None and requested.cli_days is not None:
        msg = "--cooldown cannot modify a locked environment"
        raise PipxError(msg)
    if lock_file is not None:
        return None
    # PIPX_COOLDOWN states a current machine-wide policy, so it outranks the cooldown the venv was last installed with
    return _first_cooldown(requested.cli_days, requested.env_days, stored)


def _handle_existing_install(
    venv: Venv, build: _EnvironmentBuild, options: InstallOptions, *, python: str
) -> _ExistingInstall:
    messages: Final[list[OutputMessage]] = []
    if not options.reinstall and options.force and options.python_flag_passed:
        messages.append(
            OutputMessage(
                text=pipx_wrap(
                    f"""
                    pipx ignores --python when you pass --force.
                    To reinstall {build.package_name} with {python},
                    run `pipx reinstall {venv.name} --python {python}` instead.
                    """
                )
            )
        )
    if options.force:
        messages.append(OutputMessage(text=f"Installing to existing venv {venv.name!r}"))
        return _ExistingInstall(
            continue_install=True,
            packages=(),
            skipped=(),
            messages=tuple(messages),
        )
    if options.upgrade:
        reason, upgrade_messages = _upgrade_existing_venv(venv, build, options)
        messages.extend(upgrade_messages)
        return _ExistingInstall(
            continue_install=False,
            packages=(_installed_package(venv, build.package_name),) if reason is None else (),
            skipped=(_SkippedInstall(environment=venv.name, package=build.package_name, reason=reason),)
            if reason is not None
            else (),
            messages=tuple(messages),
        )

    installed_version: Final[str] = venv.pipx_metadata.main_package.package_version
    messages.append(
        OutputMessage(
            text=pipx_wrap(
                f"""
                {venv.name!r}{f" ({installed_version})" if installed_version else ""} is already installed. Not
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
        skipped=(_SkippedInstall(environment=venv.name, package=build.package_name, reason="already-installed"),),
        messages=tuple(messages),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class _ExistingInstall:
    continue_install: bool
    packages: tuple[_InstalledPackage, ...]
    skipped: tuple[_SkippedInstall, ...]
    messages: tuple[OutputMessage, ...]


def _upgrade_existing_venv(
    venv: Venv, build: _EnvironmentBuild, options: InstallOptions
) -> tuple[str | None, tuple[OutputMessage, ...]]:
    package_metadata = venv.pipx_metadata.main_package
    installed_version: Final[str] = package_metadata.package_version
    if package_metadata.lock_file is not None:
        skip = ("locked", locked_package_message(venv.name))
    elif package_spec_satisfied(
        build.package_spec,
        build.package_name,
        installed_version,
        package_metadata.package_or_url or build.package_name,
    ):
        skip = (
            "already-satisfied",
            f"{build.package_name} {installed_version} already satisfies {redact_url_credentials(build.package_spec)}",
        )
    elif package_metadata.pinned:
        skip = ("pinned", f"Not upgrading pinned package {venv.name}. Run `pipx unpin {venv.name}` to unpin it.")
    else:
        skip = None
    if skip is not None:
        validate_expected_apps(venv, build.package_name, build.expected_apps)
        _record_expected_apps(venv, build.expected_apps)
        reason, message = skip
        return reason, (OutputMessage(text=message),)

    with preserve_venv(venv.root, enabled=bool(build.expected_apps)):
        main_pip_args: Final[list[str]] = options.pip_args or trusted_recorded_pip_args(
            package_metadata.pip_args, venv.root
        )
        venv.check_upgrade_shared_libs(pip_args=main_pip_args, verbose=options.verbose)
        venv.upgrade_packaging_libraries(main_pip_args)
        previous_resource_paths: Final[set[Path]] = get_expected_venv_resource_paths(
            venv, options.local_bin_dir, options.local_man_dir
        )
        venv.upgrade_package(
            build.package_name,
            build.package_spec,
            main_pip_args,
            exposure=ExposureOptions.recorded(package_metadata),
            is_main_package=True,
            upgrade_only_pip_args=[f"--upgrade-strategy={options.upgrade_strategy}"]
            if options.upgrade_strategy is not None
            else None,
            expected_apps=build.expected_apps,
            cooldown_days=build.cooldown_days,
        )
        validate_expected_apps(venv, build.package_name, build.expected_apps)
        package_metadata = venv.pipx_metadata.main_package
        if venv.pipx_metadata.exposure_enabled:
            expose_package_resources(package_metadata, options.local_bin_dir, options.local_man_dir, force=False)
            remove_stale_venv_resources(previous_resource_paths, venv, options.local_bin_dir, options.local_man_dir)
    return None, (
        OutputMessage(
            text=pipx_wrap(
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


@dataclass(frozen=True, slots=True, kw_only=True)
class _InstalledPackage:
    environment: str
    package: str
    version: str
    location: str
    interpreter: str | None
    backend: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _SkippedInstall:
    environment: str
    package: str
    reason: str


def _record_install_failure(
    failures: list[_FailedInstall],
    messages: list[OutputMessage],
    environment: str,
    error: PipxError,
) -> None:
    failures.append(_FailedInstall(environment=environment, error=_error_report(error)))
    messages.append(OutputMessage(text=str(error), stream=OutputStream.STDERR, level=OutputLevel.ERROR))


@dataclass(frozen=True, slots=True, kw_only=True)
class _FailedInstall:
    environment: str
    error: str


# holds everything needed to fill a venv, letting pipx repeat it when the first interpreter turns out unsupported
@dataclass(frozen=True, slots=True, kw_only=True)
class _EnvironmentBuild:
    venv_args: list[str]
    pip_args: list[str]
    override_shared: bool
    exposure_enabled: bool
    preinstall_packages: list[str] | None
    package_name: str
    package_spec: str
    force_reinstall: bool
    exposure: ExposureOptions
    expected_apps: tuple[str, ...]
    lock_file: Path | None
    cooldown_days: int | None
    pinned: bool

    def run(self, venv: Venv) -> VenvMetadata:
        venv.create_venv(self.venv_args, self.pip_args, override_shared=self.override_shared)
        venv.pipx_metadata.exposure_enabled = self.exposure_enabled
        venv.pipx_metadata.environment = venv.root.name
        # pipx writes the record last; a kill before it must not leave what looks like a pre-0.15 environment
        with marked_unfinished(venv.root):
            for dependency in self.preinstall_packages or []:
                venv.upgrade_package_no_metadata(dependency, self.pip_args, cooldown_days=self.cooldown_days)
            return venv.install_package(
                package_name=self.package_name,
                package_or_url=self.package_spec,
                pip_args=self.pip_args,
                install_only_pip_args=["--force-reinstall"] if self.force_reinstall else None,
                exposure=self.exposure,
                is_main_package=True,
                expected_apps=self.expected_apps,
                lock_file=self.lock_file,
                cooldown_days=self.cooldown_days,
                pinned=self.pinned,
            )


def _install_on_supported_python(
    venv: Venv,
    build: _EnvironmentBuild,
    options: InstallOptions,
    *,
    venv_backup: VenvBackup,
    messages: list[OutputMessage],
) -> Venv:
    try:
        # uv installs onto an interpreter above the package's upper bound, so ask the metadata as well
        constraint = build.run(venv).unsupported_python
    except IncompatiblePythonError as error:
        constraint = error.constraint
    if constraint is None:
        return venv

    interpreter: Final[str] = _supported_python(
        constraint,
        fetch_python=options.fetch_python,
        python_flag_passed=options.python_flag_passed,
        messages=messages,
    )
    venv_backup.remove_venv()
    # the rebuild deletes the recorded backend; resolving it again could switch installer and index
    rebuilt: Final[Venv] = Venv(
        venv.root, python=interpreter, verbose=options.verbose, backend=BackendOptions(cli=venv.backend_name)
    )
    build.run(rebuilt)
    return rebuilt


def install_all(spec_metadata_file: Path, options: InstallOptions) -> ExitCode:
    venvs_metadata: Final[list[PipxMetadata]] = []
    malformed: PipxError | None = None
    try:
        for venv_metadata in _extract_venv_metadata(spec_metadata_file):
            venvs_metadata.append(venv_metadata)
    except PipxError as error:
        # a one-by-one install reached a malformed entry only after the entries before it; install those first
        if not venvs_metadata:
            raise
        malformed = error
    venv_container: Final[VenvContainer] = VenvContainer(paths.CTX.venvs)
    with expose_shared_resources_in_order(venvs_metadata, options.local_bin_dir, options.local_man_dir):
        outcomes: Final[list[tuple[str, bool]]] = fan_out(
            [partial(_install_spec_venv, venv_container, venv_metadata, options) for venv_metadata in venvs_metadata],
            sequential=options.verbose,
        )
    if malformed is not None:
        raise malformed
    if not any(succeeded for _, succeeded in outcomes):
        print(  # ruff:ignore[print]  # user-facing CLI output
            f"No packages installed after running 'pipx install-all {spec_metadata_file}' {SLEEP}"
        )
    if failed := [environment for environment, succeeded in outcomes if not succeeded]:
        msg = f"The following package(s) failed to install: {', '.join(failed)}"
        raise PipxError(msg)
    return EXIT_CODE_OK


def _extract_venv_metadata(spec_metadata_file: Path) -> Iterator[PipxMetadata]:
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
        venv_metadata = PipxMetadata(paths.CTX.venvs.joinpath(package_path_name), read=False)
        try:
            venv_metadata.from_dict(entry["metadata"])
        except KeyError as exc:
            msg = f"Entry {package_path_name!r} in the spec metadata file {spec_metadata_file} is missing {exc}."
            raise PipxError(msg) from exc
        except (AttributeError, TypeError) as exc:
            msg = f"Entry {package_path_name!r} in the spec metadata file {spec_metadata_file} is malformed: {exc}"
            raise PipxError(msg) from exc
        yield venv_metadata


def _install_spec_venv(
    venv_container: VenvContainer, venv_metadata: PipxMetadata, options: InstallOptions
) -> tuple[str, bool]:
    main_package: Final[PackageInfo] = venv_metadata.main_package
    venv_dir: Final[Path] = venv_container.get_venv_dir(f"{main_package.package}{main_package.suffix}")
    interpreter: Final[str | None] = (
        options.python
        if options.python_flag_passed
        else _get_python_interpreter(venv_metadata.source_interpreter) or options.python
    )
    packages: Final[list[PackageInfo]] = [main_package, *venv_metadata.injected_packages.values()]
    try:
        package_pip_args: Final[list[list[str]]] = (
            [options.pip_args or trusted_recorded_pip_args(package.pip_args, venv_dir) for package in packages]
            if options.pip_args or options.backend.cli in {None, venv_metadata.backend}
            else _translate_recorded_pip_args(venv_metadata, packages, options.backend.cli)
        )
        with locked_in_order(venv_container.venv_lock(venv_dir)) as venv_lock:
            package_cooldown: Final[int | None] = _resolve_cooldown(
                main_package.lock_file,
                CooldownOptions(cli_days=options.cooldown.days),
                main_package.cooldown_days,
                modifies_existing=False,
            )
            installed: Final[OperationResult[InstallData]] = install(
                venv_dir,
                None,
                [_generate_package_spec(main_package)],
                InstallOptions(
                    local_bin_dir=options.local_bin_dir,
                    local_man_dir=options.local_man_dir,
                    python=interpreter,
                    pip_args=package_pip_args[0],
                    venv_args=options.venv_args or venv_metadata.venv_args,
                    verbose=options.verbose,
                    force=options.force,
                    reinstall=False,
                    exposure=ExposureOptions(
                        include_dependencies=main_package.include_dependencies,
                        include_resources_from=main_package.include_resources_from,
                        suffix=main_package.suffix,
                    ),
                    preinstall_packages=[],
                    expected_apps=main_package.expected_apps,
                    lock_file=main_package.lock_file,
                    python_flag_passed=options.python_flag_passed,
                    backend=replace(options.backend, cli=options.backend.cli or venv_metadata.backend),
                    exposure_enabled=venv_metadata.exposure_enabled,
                    replace_expected_apps=True,
                    replace_lock=True,
                    cooldown=CooldownOptions(cli_days=package_cooldown),
                    pinned=main_package.pinned,
                ),
                venv_lock=venv_lock,
            )
            # install left an existing environment alone, so its injected packages must not change it either
            for inject_package, inject_pip_args in (
                () if installed.data.skipped else zip(packages[1:], package_pip_args[1:], strict=True)
            ):
                inject(
                    venv_dir,
                    [_generate_package_spec(inject_package)],
                    [],
                    InjectOptions(
                        pip_args=inject_pip_args,
                        verbose=options.verbose,
                        include_apps=inject_package.include_apps,
                        include_dependencies=inject_package.include_dependencies,
                        include_resources_from=inject_package.include_resources_from,
                        force=options.force,
                        with_suffix=inject_package.suffix == main_package.suffix,
                        cooldown_days=_first_cooldown(options.cooldown.days, inject_package.cooldown_days),
                        pinned=inject_package.pinned,
                    ),
                )
    except PipxError as error:
        print(error, file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output
        return venv_dir.name, False
    return venv_dir.name, True


def _get_python_interpreter(source_interpreter: Path | None) -> str | None:
    if source_interpreter is None:
        return None
    if (reason := _distrusted_interpreter(source_interpreter)) is None:
        return str(source_interpreter)

    print(  # ruff:ignore[print]  # user-facing CLI output
        pipx_wrap(
            f"""
            The exported python interpreter '{source_interpreter}' is ignored
            as {reason}; using the default python instead.
            """
        )
    )

    return None


def _distrusted_interpreter(python: Path) -> str | None:
    if not python.is_file():
        return "not found"
    # the snapshot can outlive the interpreter it names, and whoever creates that path again picks what runs here
    resolved: Final[Path] = python.resolve()
    if any((path.parent.parent / "pyvenv.cfg").is_file() for path in {python, resolved}):
        return "it is inside a virtual environment, which can be removed and created again"
    if (location := changeable_by_others(python) or changeable_by_others(resolved)) is not None:
        return f"another account can change {location}"
    return None


def _translate_recorded_pip_args(
    venv_metadata: PipxMetadata, packages: list[PackageInfo], backend: str
) -> list[list[str]]:
    # recorded pip args can hold options only the recording backend accepts, such as pip's --progress-bar
    environment: Final[str] = f"{venv_metadata.main_package.package}{venv_metadata.main_package.suffix}"
    translations: Final[list[tuple[list[str], list[str]]]] = [
        translate_pip_args(trusted_recorded_pip_args(package.pip_args, venv_metadata.venv_dir), backend, environment)
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
            HAZARD,
            venv_metadata.backend,
            environment,
            " ".join(dropped),
            f"; translated for {backend}: {' '.join(kept)}" if kept else "",
        )
    return [translated for translated, _ in translations]


def _generate_package_spec(package_info: PackageInfo) -> str:
    if not package_info.package_or_url:
        msg = f"A package spec is not available for {package_info.package}"
        raise PipxError(msg)

    if package_info.package == package_info.package_or_url:
        return f"{package_info.package}=={package_info.package_version}"
    return package_info.package_or_url


__all__ = [
    "InstallData",
    "install",
    "install_all",
]
