from __future__ import annotations

__lazy_modules__ = [
    "functools",
    "packaging.utils",
    "pathlib",
    "pipx",
    "pipx.backends",
    "pipx.commands.common",
    "pipx.commands.transaction",
    "pipx.package_specifier",
    "pipx.util",
    "pipx.venv",
    "pipx.wrap",
    "re",
]

import logging
import os
import re
from dataclasses import dataclass
from enum import StrEnum
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Final

from packaging.utils import canonicalize_name

from pipx import paths
from pipx.backends import UV, assert_not_pip_under_uv
from pipx.colors import BOLD
from pipx.commands.common import (
    get_expected_venv_resource_paths,
    package_name_from_spec,
    run_post_install_actions,
)
from pipx.commands.transaction import marked_unfinished, preserve_venv
from pipx.constants import EXIT_CODE_INJECT_ERROR, EXIT_CODE_OK
from pipx.emojis import HAZARD, STARS
from pipx.package_specifier import add_extras, get_extras, source_without_extras, trusted_recorded_pip_args
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
from pipx.util import InstalledNameMismatchError, PipxError, redact_url_credentials
from pipx.venv import Venv
from pipx.wrap import pipx_wrap

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Sequence

    from pipx.pipx_metadata_file import PackageInfo
    from pipx.venv_inspect import VenvMetadata

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def inject_dep(  # ruff:ignore[too-many-arguments, too-many-locals]  # inject resolves the full package/venv context inline; a struct would only relocate it
    venv_dir: Path,
    package_name: str | None,
    package_spec: str,
    pip_args: list[str],
    *,
    verbose: bool,
    include_apps: bool,
    include_dependencies: bool,
    include_resources_from: Sequence[str],
    force: bool,
    force_reinstall: bool = True,
    suffix: bool,
    backend: str | None,
    env_backend: str | None,
    cooldown_days: int | None,
    pinned: bool | None,
    emit_output: bool,
) -> OperationResult[InjectionData]:
    _LOGGER.debug("Injecting package %s", redact_url_credentials(package_spec))

    if not venv_dir.exists() or next(venv_dir.iterdir(), None) is None:
        msg = f"""
            Can't inject {redact_url_credentials(package_spec)!r} into nonexistent Virtual Environment
            {venv_dir.name!r}. Be sure to install the package first with 'pipx
            install {venv_dir.name}' before injecting into it.
            """
        raise PipxError(msg)

    venv: Final[Venv] = Venv(venv_dir, verbose=verbose, backend=backend, env_backend=env_backend)
    if not venv.package_metadata:
        msg = f"""
            Can't inject {redact_url_credentials(package_spec)!r} into Virtual Environment
            {venv.name!r}. {venv.name!r} has no internal pipx metadata, which
            pipx versions before 0.15.0.0 did not record. Uninstall and install
            {venv.name!r}, or run 'pipx reinstall-all', to fix it.
            """
        raise PipxError(msg)
    if (lock_file := venv.pipx_metadata.main_package.lock_file) is not None:
        msg = (
            f"Cannot inject into locked environment {venv.name}. "
            f"Update {lock_file} and run `pipx reinstall {venv.name}`."
        )
        raise PipxError(msg)
    if cooldown_days is None:
        cooldown_days = venv.pipx_metadata.main_package.cooldown_days
    venv.check_upgrade_shared_libs(pip_args=pip_args, verbose=verbose)

    # the spec can be anything pip installs, such as a VCS URL or an archive, so only resolving it gives the name
    if package_name is None:
        package_name = package_name_from_spec(
            package_spec,
            os.fspath(venv.python_path),
            pip_args=pip_args,
            verbose=verbose,
            backend=venv.backend_name,
            env_backend=env_backend,
            cooldown_days=cooldown_days,
        )

    # as at install: pip in a uv venv works for `pipx run` but breaks anyone reaching for the venv's missing pip
    assert_not_pip_under_uv(canonicalize_name(package_name), venv.backend_name)

    is_main_package: Final[bool] = canonicalize_name(package_name) == canonicalize_name(venv.main_package_name)
    already_installed: Final[bool] = not force and venv.has_package(package_name)
    main_spec: Final[str | None] = (
        _main_spec_with_extras(venv, package_spec) if already_installed and is_main_package else None
    )
    if already_installed and main_spec is None:
        _LOGGER.info("Package %s is already installed", package_name)
        return _finish_inject(
            OperationResult(
                command=("inject",),
                data=InjectionData(
                    packages=(),
                    skipped=(_InjectionSkip(environment=venv.name, package=package_name, reason="already-installed"),),
                ),
                messages=(
                    OutputMessage(
                        text=pipx_wrap(
                            f"""
                            {HAZARD} {package_name} is already installed in {venv.name!r}.
                            Not modifying existing installation in '{venv_dir}'.
                            Pass '--force' to force installation.
                            """
                        )
                    ),
                ),
            ),
            emit_output=emit_output,
        )

    package_spec = main_spec or package_spec
    if is_main_package:
        main_package: Final[PackageInfo] = venv.pipx_metadata.main_package
        pip_args = pip_args or trusted_recorded_pip_args(main_package.pip_args, venv_dir)
        include_dependencies = main_package.include_dependencies
        include_resources_from = main_package.include_resources_from
        include_apps = main_package.include_apps
        venv_suffix = main_package.suffix
        pinned = main_package.pinned
    elif suffix:
        venv_suffix = venv.package_metadata[venv.main_package_name].suffix
    else:
        venv_suffix = ""
    # pip's --force-reinstall covers the whole resolution, so it also refetches the main package by name from this
    # package's index when this package depends on it; uv can limit the reinstall to this package
    reinstall_args: Final[list[str] | None] = (
        (["--reinstall-package", package_name] if venv.backend_name == UV else ["--force-reinstall"])
        if force and force_reinstall and venv.has_package(package_name)
        else None
    )
    previous_resource_paths: Final[set[Path]] = get_expected_venv_resource_paths(
        venv, paths.CTX.bin_dir, paths.CTX.man_dir
    )
    messages: Final[list[OutputMessage]] = []
    # like install, a package without the apps --include-apps asked for leaves the venv as it was
    with (
        preserve_venv(venv_dir, enabled=include_apps or bool(include_resources_from)),
        marked_unfinished(venv_dir),
    ):
        package_name = _install_under_installed_name(
            partial(
                venv.install_package,
                package_or_url=package_spec,
                pip_args=pip_args,
                install_only_pip_args=reinstall_args,
                include_dependencies=include_dependencies,
                include_resources_from=include_resources_from,
                include_apps=include_apps,
                is_main_package=is_main_package,
                suffix=venv_suffix,
                pinned=pinned,
                cooldown_days=cooldown_days,
            ),
            package_name,
        )
        if include_apps:
            messages.extend(
                run_post_install_actions(
                    venv,
                    package_name,
                    paths.CTX.bin_dir,
                    paths.CTX.man_dir,
                    venv_dir,
                    force=force,
                    previous_resource_paths=previous_resource_paths,
                ),
            )

    if is_main_package:
        messages.append(OutputMessage(text=f"  updated package {BOLD(package_name)} in venv {BOLD(venv.name)}"))
    else:
        messages.append(OutputMessage(text=f"  injected package {BOLD(package_name)} into venv {BOLD(venv.name)}"))
    messages.append(OutputMessage(text=f"done! {STARS}", stream=OutputStream.STDERR))
    package: Final[PackageInfo] = venv.package_metadata[package_name]
    return _finish_inject(
        OperationResult(
            command=("inject",),
            data=InjectionData(
                packages=(
                    InjectionPackage(
                        environment=venv.name,
                        package=f"{package.package}{package.suffix}",
                        version=package.package_version,
                        status=InjectionStatus.UPDATED if is_main_package else InjectionStatus.INJECTED,
                        location=str(venv.root),
                    ),
                ),
                skipped=(),
            ),
            messages=tuple(messages),
        ),
        emit_output=emit_output,
    )


def _main_spec_with_extras(venv: Venv, package_spec: str) -> str | None:
    # without --force only extras may change, so naming the package cannot swap the recorded path or URL for the index's
    if not (extras := get_extras(package_spec)) or (recorded := venv.pipx_metadata.main_package.package_or_url) is None:
        return None
    try:
        recorded_source: Final[str] = source_without_extras(recorded)
    except PipxError as error:
        msg = (
            f"The recorded source {redact_url_credentials(recorded)} of {venv.name!r} no longer exists. "
            f"Pass '--force' to install {redact_url_credentials(package_spec)!r} in its place."
        )
        raise PipxError(msg) from error
    name: Final[str] = canonicalize_name(venv.main_package_name)
    # NAME[extra] @ URL names the same source as a bare recorded URL
    if source_without_extras(package_spec) not in {name, recorded_source, f"{name} @ {recorded_source}"}:
        return None
    return add_extras(recorded, venv.main_package_name, extras)


def _finish_inject(
    result: OperationResult[InjectionData],
    *,
    emit_output: bool,
) -> OperationResult[InjectionData]:
    if not emit_output:
        return result
    if result.errors:
        render_messages(
            tuple(message for message in result.messages if message.level is OutputLevel.NORMAL),
            quiet=0,
        )
        raise PipxError(result.errors[0].message)
    render_result(result, output=OutputFormat.HUMAN, quiet=0)
    return result


def _install_under_installed_name(install: Callable[[str], VenvMetadata], package_name: str) -> str:
    try:
        install(package_name)
    except InstalledNameMismatchError as error:
        # the spec built under another name than the one pipx resolved, so record the package the venv now holds
        install(error.installed_name)
        return error.installed_name
    return package_name


def inject(  # ruff:ignore[too-many-arguments]  # inject mirrors inject_dep's flat CLI-facing option set
    venv_dir: Path,
    package_specs: Iterable[str],
    requirement_files: Iterable[str],
    pip_args: list[str],
    *,
    verbose: bool,
    include_apps: bool,
    include_dependencies: bool,
    include_resources_from: Sequence[str],
    force: bool,
    suffix: bool,
    backend: str | None = None,
    env_backend: str | None = None,
    cooldown_days: int | None,
    pinned: bool | None = None,
    emit_output: bool = True,
) -> OperationResult[InjectionData]:
    package_set: Final[set[str]] = set(package_specs)
    for filename in requirement_files:
        package_set.update(_parse_requirements(filename))
    packages: Final[list[str]] = sorted(package_set)

    if not packages:
        error: Final[str] = "No packages to inject; pass a package spec or --requirement."
        return _finish_inject(
            OperationResult(
                command=("inject",),
                data=InjectionData(packages=(), skipped=()),
                messages=(OutputMessage(text=error, stream=OutputStream.STDERR, level=OutputLevel.ERROR),),
                exit_code=EXIT_CODE_INJECT_ERROR,
                errors=(OperationError(code="package_inject_failed", message=error, environment=venv_dir.name),),
            ),
            emit_output=emit_output,
        )
    _LOGGER.info("Injecting packages: %r", [redact_url_credentials(package) for package in packages])

    changed: Final[list[InjectionPackage]] = []
    errors: Final[list[OperationError]] = []
    messages: Final[list[OutputMessage]] = []
    skipped: Final[list[_InjectionSkip]] = []
    for dependency in packages:
        try:
            result: OperationResult[InjectionData] = inject_dep(
                venv_dir,
                package_name=None,
                package_spec=dependency,
                pip_args=pip_args,
                verbose=verbose,
                include_apps=include_apps or include_dependencies or bool(include_resources_from),
                include_dependencies=include_dependencies,
                include_resources_from=include_resources_from,
                force=force,
                suffix=suffix,
                backend=backend,
                env_backend=env_backend,
                cooldown_days=cooldown_days,
                pinned=pinned,
                emit_output=False,
            )
        except PipxError as error:
            errors.append(
                OperationError(
                    code="package_inject_failed",
                    message=error.raw_message,
                    environment=venv_dir.name,
                    package=redact_url_credentials(dependency),
                )
            )
            messages.append(OutputMessage(text=str(error), stream=OutputStream.STDERR, level=OutputLevel.ERROR))
            break
        changed.extend(result.data.packages)
        skipped.extend(result.data.skipped)
        messages.extend(result.messages)

    return _finish_inject(
        OperationResult(
            command=("inject",),
            data=InjectionData(packages=tuple(changed), skipped=tuple(skipped)),
            messages=tuple(messages),
            exit_code=EXIT_CODE_INJECT_ERROR if errors else EXIT_CODE_OK,
            errors=tuple(errors),
            succeeded=bool(changed or skipped),
        ),
        emit_output=emit_output,
    )


def _parse_requirements(filename: str) -> Iterator[str]:
    # strips comments the way pip does: https://github.com/pypa/pip/blob/main/src/pip/_internal/req/req_file.py
    comment: Final[re.Pattern[str]] = re.compile(r"(^|\s+)#.*$")
    with Path(filename).open(encoding="utf-8") as requirements:
        for line in requirements:
            if spec := comment.sub("", line).strip():
                yield spec


class InjectionStatus(StrEnum):
    INJECTED = "injected"
    UNINJECTED = "uninjected"
    UPDATED = "updated"


@dataclass(frozen=True, slots=True, kw_only=True)
class InjectionPackage:
    environment: str
    package: str
    version: str
    status: InjectionStatus
    location: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _InjectionSkip:
    environment: str
    package: str
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class InjectionData(OperationData):
    packages: tuple[InjectionPackage, ...]
    skipped: tuple[_InjectionSkip, ...]


__all__ = [
    "InjectionData",
    "InjectionPackage",
    "InjectionStatus",
    "inject",
    "inject_dep",
]
