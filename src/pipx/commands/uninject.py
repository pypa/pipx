from __future__ import annotations

__lazy_modules__ = [
    "packaging.utils",
    "pathlib",
    "pipx",
    "pipx.commands.common",
    "pipx.commands.inject",
    "pipx.redact",
    "pipx.trash",
    "pipx.venv",
    "pipx.venv_inspect",
    "pipx.wrap",
]

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Final

from packaging.utils import canonicalize_name

from pipx import paths
from pipx.colors import BOLD
from pipx.commands.common import (
    drop_copies_claimed_elsewhere,
    drop_links_taken_over,
    exposed_app_names,
    get_expected_venv_resource_paths,
    get_package_bin_dir_app_paths,
    get_package_completion_paths,
    get_package_man_paths,
)
from pipx.commands.inject import (
    InjectionData,
    InjectionPackage,
    InjectionStatus,
)
from pipx.constants import (
    COMPLETION_SECTIONS,
    EXIT_CODE_OK,
    EXIT_CODE_UNINJECT_ERROR,
    MAN_SECTIONS,
)
from pipx.emojis import STARS
from pipx.redact import redact_url_credentials
from pipx.result import OperationError, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.trash import safe_unlink
from pipx.venv import Venv
from pipx.venv_inspect import (
    fetch_info_in_venv,
    get_distributions_by_name,
    get_required_dependency_names,
    not_required_packages,
)
from pipx.wrap import pipx_wrap

if TYPE_CHECKING:
    from importlib import metadata

    from pipx.options import UninjectOptions
    from pipx.pipx_metadata_file import PackageInfo

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def uninject(venv_dir: Path, dependencies: list[str], options: UninjectOptions) -> OperationResult[InjectionData]:
    if not venv_dir.exists() or next(venv_dir.iterdir(), None) is None:
        return _uninject_failure(
            venv_dir.name,
            None,
            f"Virtual environment {venv_dir.name} does not exist.",
            stream=OutputStream.STDERR,
        )

    venv: Final[Venv] = Venv(venv_dir, verbose=options.verbose)

    if not venv.package_metadata:
        return _uninject_failure(
            venv.name,
            None,
            pipx_wrap(
                f"""
                Can't uninject from Virtual Environment {venv_dir.name!r}.
                {venv_dir.name!r} has no internal pipx metadata.
                pipx versions before 0.15.0.0 did not record it.
                Uninstall and install {venv_dir.name!r} manually to fix it.
                """
            ),
            stream=OutputStream.STDERR,
        )

    errors: Final[list[OperationError]] = []
    messages: Final[list[OutputMessage]] = []
    packages: Final[list[InjectionPackage]] = []
    for dependency in dependencies:
        result: OperationResult[InjectionData] = _uninject_dep(
            venv,
            dependency,
            local_bin_dir=options.local_bin_dir,
            local_man_dir=options.local_man_dir,
            leave_deps=options.leave_deps,
        )
        errors.extend(result.errors)
        messages.extend(result.messages)
        packages.extend(result.data.packages)

    return OperationResult(
        command=("uninject",),
        data=InjectionData(packages=tuple(packages), skipped=()),
        messages=tuple(messages),
        exit_code=EXIT_CODE_UNINJECT_ERROR if errors else EXIT_CODE_OK,
        errors=tuple(errors),
        succeeded=bool(packages),
    )


def _uninject_failure(
    environment: str,
    package: str | None,
    error: str,
    *,
    stream: OutputStream = OutputStream.LOG,
) -> OperationResult[InjectionData]:
    return OperationResult(
        command=("uninject",),
        data=InjectionData(packages=(), skipped=()),
        messages=(OutputMessage(text=error, stream=stream, level=OutputLevel.ERROR),),
        exit_code=EXIT_CODE_UNINJECT_ERROR,
        errors=(
            OperationError(code="package_uninject_failed", message=error, environment=environment, package=package),
        ),
    )


def _uninject_dep(
    venv: Venv,
    package_name: str,
    *,
    local_bin_dir: Path,
    local_man_dir: Path,
    leave_deps: bool,
) -> OperationResult[InjectionData]:
    package_name = _injected_metadata_name(venv, canonicalize_name(package_name))

    if package_name == venv.pipx_metadata.main_package.package:
        return _uninject_failure(
            venv.name,
            package_name,
            pipx_wrap(
                f"""
                {package_name} is the main package of {venv.root.name}
                venv. Use `pipx uninstall {venv.root.name}` to uninstall instead of uninject.
                """,
                subsequent_indent=" " * 4,
            ),
        )

    if package_name not in venv.pipx_metadata.injected_packages:
        return _uninject_failure(
            venv.name,
            masked_name := redact_url_credentials(package_name),
            f"{masked_name} is not in the {venv.root.name} venv. Skipping.",
        )

    package: Final[PackageInfo] = venv.package_metadata[package_name]
    resource_paths: Final[set[Path]] = drop_copies_claimed_elsewhere(
        _get_include_resource_paths(package, venv, local_bin_dir, local_man_dir), venv.bin_path
    )

    if not leave_deps:
        orig_not_required_packages: Final[set[str]] = venv.list_installed_packages(not_required=True)
        _LOGGER.info("Original not required packages: %s", orig_not_required_packages)

    venv.uninstall_packages(package_name, was_injected=True)

    if not leave_deps:
        # inspect again: the uninstall can drop search path entries, such as an editable install's .pth
        venv_sys_path, venv_env, _ = fetch_info_in_venv(venv.python_path)
        new_not_required_packages: Final[set[str]] = not_required_packages(venv_sys_path, venv_env)
        _LOGGER.info("New not required packages: %s", new_not_required_packages)

        if deps_of_uninstalled := new_not_required_packages - orig_not_required_packages:
            deps_of_uninstalled -= _get_remaining_dependencies(venv, package_name, venv_sys_path, venv_env)
            _LOGGER.info("Dependencies of uninstalled package: %s", deps_of_uninstalled)
            if deps_of_uninstalled:
                venv.uninstall_packages(*sorted(deps_of_uninstalled))

    if package.include_apps:
        # the uninstall dropped this package's record, so what the venv still expects belongs to its other packages
        expected: Final[set[Path]] = get_expected_venv_resource_paths(venv, local_bin_dir, local_man_dir)
        for path in drop_links_taken_over(resource_paths - expected, venv.root):
            try:
                safe_unlink(path)
            except FileNotFoundError:
                _LOGGER.info("tried to remove but couldn't find %s", path)
            else:
                _LOGGER.info("removed file %s", path)

    deps_string: Final[str] = "" if leave_deps else " and its dependencies"
    return OperationResult(
        command=("uninject",),
        data=InjectionData(
            packages=(
                InjectionPackage(
                    environment=venv.name,
                    package=f"{package.package}{package.suffix}",
                    version=package.package_version,
                    status=InjectionStatus.UNINJECTED,
                    location=str(venv.root),
                ),
            ),
            skipped=(),
        ),
        messages=(
            OutputMessage(
                text=f"Uninjected package {BOLD(package_name)}{deps_string} from venv {BOLD(venv.root.name)} {STARS}"
            ),
        ),
    )


def _injected_metadata_name(venv: Venv, package_name: str) -> str:
    # metadata keys an injected package by its bare name, but `inject --with-suffix` adds the environment suffix, so
    # users spell it black@1 too
    if package_name in venv.pipx_metadata.injected_packages:
        return package_name
    for name, injected_package in venv.pipx_metadata.injected_packages.items():
        if injected_package.suffix and package_name == canonicalize_name(f"{name}{injected_package.suffix}"):
            return name
    return package_name


def _get_include_resource_paths(
    package: PackageInfo, venv: Venv, local_bin_dir: Path, local_man_dir: Path
) -> set[Path]:
    apps: Final[set[str]] = {name for app in package.apps_to_expose for name in exposed_app_names(app, package.suffix)}
    man_pages: Final[set[str]] = set(package.man_pages_to_expose)
    completions: Final[set[str]] = set(package.completions_to_expose)
    return (
        {path for path in get_package_bin_dir_app_paths(package, venv.bin_path, local_bin_dir) if path.name in apps}
        | {
            path
            for section in MAN_SECTIONS
            for path in get_package_man_paths(package, venv.man_path / section, local_man_dir / section)
            if str(Path(path.parent.name) / path.name) in man_pages
        }
        | {
            path
            for section in COMPLETION_SECTIONS
            for path in get_package_completion_paths(
                package, venv.man_path.parent / section, paths.CTX.completion_dir / section
            )
            if f"{path.parent.parent.name}/{path.parent.name}/{path.name}" in completions
        }
    )


def _get_remaining_dependencies(
    venv: Venv, excluded_package: str, venv_sys_path: list[str], venv_env: dict[str, str]
) -> set[str]:
    distributions: Final[dict[str, metadata.Distribution]] = get_distributions_by_name(venv_sys_path)
    remaining_deps: Final[set[str]] = set()
    for name in (venv.pipx_metadata.main_package.package, *venv.pipx_metadata.injected_packages):
        if name is not None and name != excluded_package:
            remaining_deps.update(_collect_transitive_deps(name, distributions, venv_env))
    return remaining_deps


def _collect_transitive_deps(
    package_name: str,
    distributions: dict[str, metadata.Distribution],
    env: dict[str, str],
    visited: set[str] | None = None,
) -> set[str]:
    if visited is None:
        visited = set()
    if (canonical := canonicalize_name(package_name)) in visited:
        return visited
    visited.add(canonical)
    if distribution := distributions.get(canonical):
        for dependency_name in get_required_dependency_names(distribution, env):
            _collect_transitive_deps(dependency_name, distributions, env, visited)
    return visited


__all__ = [
    "uninject",
]
