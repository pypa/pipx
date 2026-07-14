from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Final

from packaging.utils import canonicalize_name

from pipx import paths
from pipx.backends import assert_not_pip_under_uv
from pipx.colors import bold
from pipx.commands.common import (
    get_expected_venv_resource_paths,
    package_name_from_spec,
    run_post_install_actions,
)
from pipx.commands.transaction import preserve_venv
from pipx.constants import EXIT_CODE_INJECT_ERROR, EXIT_CODE_OK
from pipx.emojis import hazard, stars
from pipx.package_specifier import get_extras
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
from pipx.util import PipxError, pipx_wrap
from pipx.venv import Venv

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Sequence
    from pathlib import Path

    from pipx.pipx_metadata_file import PackageInfo

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

_COMMENT_RE: Final[re.Pattern[str]] = re.compile(r"(^|\s+)#.*$")


def inject_dep(
    venv_dir: Path,
    package_name: str | None,
    package_spec: str,
    pip_args: list[str],
    *,
    verbose: bool,
    include_apps: bool,
    include_dependencies: bool,
    include_apps_from: Sequence[str],
    force: bool,
    suffix: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
    cooldown_days: int | None = None,
    emit_output: bool = True,
) -> OperationResult[InjectionData]:
    _LOGGER.debug("Injecting package %s", package_spec)

    if not venv_dir.exists() or next(venv_dir.iterdir(), None) is None:
        raise PipxError(
            f"""
            Can't inject {package_spec!r} into nonexistent Virtual Environment
            {venv_dir.name!r}. Be sure to install the package first with 'pipx
            install {venv_dir.name}' before injecting into it.
            """
        )

    venv = Venv(venv_dir, verbose=verbose, backend=backend, env_backend=env_backend)
    if not venv.package_metadata:
        raise PipxError(
            f"""
            Can't inject {package_spec!r} into Virtual Environment
            {venv.name!r}. {venv.name!r} has missing internal pipx metadata. It
            was likely installed using a pipx version before 0.15.0.0. Please
            uninstall and install {venv.name!r}, or reinstall-all to fix.
            """
        )
    if (lock_file := venv.pipx_metadata.main_package.lock_file) is not None:
        raise PipxError(
            f"Cannot inject into locked environment {venv.name}. "
            f"Update {lock_file} and run `pipx reinstall {venv.name}`."
        )
    if cooldown_days is None:
        cooldown_days = venv.pipx_metadata.main_package.cooldown_days
    venv.check_upgrade_shared_libs(pip_args=pip_args, verbose=verbose)

    # package_spec is anything pip-installable, including package_name, vcs spec,
    #   zip file, or tar.gz file.
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

    # Mirrors the install-side guard: dropping pip into a uv venv works for
    # ``pipx run`` but breaks anyone reaching for the venv's missing pip.
    assert_not_pip_under_uv(canonicalize_name(package_name), venv.backend_name)

    is_main_package = canonicalize_name(package_name) == canonicalize_name(venv.main_package_name)
    if not force and venv.has_package(package_name) and (not is_main_package or not get_extras(package_spec)):
        _LOGGER.info("Package %s is already installed", package_name)
        return _finish_inject(
            OperationResult(
                command="inject",
                data=InjectionData(
                    packages=(),
                    skipped=(InjectionSkip(venv.name, package_name, "already-installed"),),
                    failures=(),
                ),
                messages=(
                    OutputMessage(
                        pipx_wrap(
                            f"""
                            {hazard} {package_name} already seems to be installed in {venv.name!r}.
                            Not modifying existing installation in '{venv_dir}'.
                            Pass '--force' to force installation.
                            """
                        )
                    ),
                ),
            ),
            emit_output=emit_output,
        )

    pinned = False
    if is_main_package:
        main_package = venv.pipx_metadata.main_package
        pip_args = pip_args or main_package.pip_args
        include_dependencies = main_package.include_dependencies
        include_apps_from = main_package.include_apps_from
        include_apps = main_package.include_apps
        venv_suffix = main_package.suffix
        pinned = main_package.pinned
    elif suffix:
        venv_suffix = venv.package_metadata[venv.main_package_name].suffix
    else:
        venv_suffix = ""
    previous_resource_paths: Final[set[Path]] = get_expected_venv_resource_paths(
        venv, paths.ctx.bin_dir, paths.ctx.man_dir
    )
    messages: Final[list[OutputMessage]] = []
    with preserve_venv(venv_dir, enabled=bool(include_apps_from)):
        venv.install_package(
            package_name=package_name,
            package_or_url=package_spec,
            pip_args=pip_args,
            install_only_pip_args=["--force-reinstall"] if force else None,
            include_dependencies=include_dependencies,
            include_apps_from=include_apps_from,
            include_apps=include_apps,
            is_main_package=is_main_package,
            suffix=venv_suffix,
            pinned=pinned,
            cooldown_days=cooldown_days,
        )
        if include_apps:
            messages.extend(
                run_post_install_actions(
                    venv,
                    package_name,
                    paths.ctx.bin_dir,
                    paths.ctx.man_dir,
                    venv_dir,
                    force=force,
                    previous_resource_paths=previous_resource_paths,
                ),
            )

    status: Final[InjectionStatus] = InjectionStatus.UPDATED if is_main_package else InjectionStatus.INJECTED
    if is_main_package:
        messages.append(OutputMessage(f"  updated package {bold(package_name)} in venv {bold(venv.name)}"))
    else:
        messages.append(OutputMessage(f"  injected package {bold(package_name)} into venv {bold(venv.name)}"))
    messages.append(OutputMessage(f"done! {stars}", stream=OutputStream.STDERR))
    package: Final[PackageInfo] = venv.package_metadata[package_name]
    return _finish_inject(
        OperationResult(
            command="inject",
            data=InjectionData(
                packages=(
                    InjectionPackage(
                        environment=venv.name,
                        package=f"{package.package}{package.suffix}",
                        version=package.package_version,
                        status=status,
                        location=str(venv.root),
                    ),
                ),
                skipped=(),
                failures=(),
            ),
            messages=tuple(messages),
        ),
        emit_output=emit_output,
    )


def inject(
    venv_dir: Path,
    package_specs: Iterable[str],
    requirement_files: Iterable[str],
    pip_args: list[str],
    *,
    verbose: bool,
    include_apps: bool,
    include_dependencies: bool,
    include_apps_from: Sequence[str],
    force: bool,
    suffix: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
    cooldown_days: int | None = None,
    emit_output: bool = True,
) -> OperationResult[InjectionData]:
    package_set: Final[set[str]] = set(package_specs)
    for filename in requirement_files:
        package_set.update(parse_requirements(filename))
    packages: Final[list[str]] = sorted(package_set)

    if not packages:
        return _finish_inject(
            _inject_failure(venv_dir.name, None, "No packages have been specified."),
            emit_output=emit_output,
        )
    _LOGGER.info("Injecting packages: %r", packages)

    expose_apps: Final[bool] = include_apps or include_dependencies or bool(include_apps_from)
    changed: Final[list[InjectionPackage]] = []
    failures: Final[list[InjectionFailure]] = []
    messages: Final[list[OutputMessage]] = []
    skipped: Final[list[InjectionSkip]] = []
    for dependency in packages:
        try:
            result: OperationResult[InjectionData] = inject_dep(
                venv_dir,
                package_name=None,
                package_spec=dependency,
                pip_args=pip_args,
                verbose=verbose,
                include_apps=expose_apps,
                include_dependencies=include_dependencies,
                include_apps_from=include_apps_from,
                force=force,
                suffix=suffix,
                backend=backend,
                env_backend=env_backend,
                cooldown_days=cooldown_days,
                emit_output=False,
            )
        except PipxError as error:
            failures.append(InjectionFailure(venv_dir.name, dependency, error.raw_message))
            messages.append(OutputMessage(str(error), stream=OutputStream.STDERR, level=OutputLevel.ERROR))
            break
        changed.extend(result.data.packages)
        skipped.extend(result.data.skipped)
        messages.extend(result.messages)

    return _finish_inject(
        OperationResult(
            command="inject",
            data=InjectionData(packages=tuple(changed), skipped=tuple(skipped), failures=tuple(failures)),
            messages=tuple(messages),
            exit_code=EXIT_CODE_INJECT_ERROR if failures else EXIT_CODE_OK,
        ),
        emit_output=emit_output,
    )


def _inject_failure(environment: str, package: str | None, error: str) -> OperationResult[InjectionData]:
    return OperationResult(
        command="inject",
        data=InjectionData(packages=(), skipped=(), failures=(InjectionFailure(environment, package, error),)),
        messages=(OutputMessage(error, stream=OutputStream.STDERR, level=OutputLevel.ERROR),),
        exit_code=EXIT_CODE_INJECT_ERROR,
    )


def _finish_inject(
    result: OperationResult[InjectionData],
    *,
    emit_output: bool,
) -> OperationResult[InjectionData]:
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


def parse_requirements(filename: str | os.PathLike) -> Generator[str, None, None]:
    """
    Extract package specifications from requirements file.

    Return all of the non-empty lines with comments removed.
    """
    # Based on https://github.com/pypa/pip/blob/main/src/pip/_internal/req/req_file.py
    with open(filename) as f:
        for line in f:
            # Strip comments and filter empty lines
            if pkgspec := _COMMENT_RE.sub("", line).strip():
                yield pkgspec


class InjectionStatus(str, Enum):
    INJECTED = "injected"
    UNINJECTED = "uninjected"
    UPDATED = "updated"


@dataclass(frozen=True)
class InjectionPackage:
    environment: str
    package: str
    version: str
    status: InjectionStatus
    location: str


@dataclass(frozen=True)
class InjectionSkip:
    environment: str
    package: str
    reason: str


@dataclass(frozen=True)
class InjectionFailure:
    environment: str
    package: str | None
    error: str


@dataclass(frozen=True)
class InjectionData(OperationData):
    packages: tuple[InjectionPackage, ...]
    skipped: tuple[InjectionSkip, ...]
    failures: tuple[InjectionFailure, ...]


__all__ = [
    "InjectionData",
    "InjectionFailure",
    "InjectionPackage",
    "InjectionSkip",
    "InjectionStatus",
    "inject",
    "inject_dep",
    "parse_requirements",
]
