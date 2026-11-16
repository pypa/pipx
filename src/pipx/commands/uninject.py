from __future__ import annotations

__lazy_modules__ = [
    "packaging.utils",
    "pathlib",
    "pipx.commands.common",
    "pipx.commands.inject",
    "pipx.paths",
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
from pipx.paths import CTX
from pipx.redact import redact_url_credentials
from pipx.result import OperationError, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.trash import safe_unlink
from pipx.venv import Venv
from pipx.venv_inspect import (
    fetch_info_in_venv,
    get_distributions_by_name,
    get_required_dependency_names,
)
from pipx.wrap import pipx_wrap

if TYPE_CHECKING:
    from pipx.options import UninjectOptions
    from pipx.pipx_metadata_file import PackageInfo

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def uninject(venv_dir: Path, dependencies: list[str], options: UninjectOptions) -> OperationResult[InjectionData]:
    """Remove dependencies that were injected into an environment.

    :param venv_dir: the directory of the environment.
    :param dependencies: the names of the packages to remove.
    :param options: the options of the removal.
    :returns: the result listing the removed packages, and the failures.
    """
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
    requested: Final[str] = canonicalize_name(package_name)
    # metadata keys an injected package by the name the installer reported, which pip leaves as declared (Mixed_Case),
    # and `inject --with-suffix` adds the environment suffix, so users spell it black@1 too
    package_name = next(
        (
            name
            for name, injected_package in venv.pipx_metadata.injected_packages.items()
            if requested in {canonicalize_name(name), canonicalize_name(f"{name}{injected_package.exposure.suffix}")}
        ),
        requested,
    )

    if canonicalize_name(package_name) == canonicalize_name(venv.main_package_name):
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
        # once the package is gone, nothing records what it pulled in
        requirements_before: Final[dict[str, set[str]]] = _requirements_by_name(venv.python_path)

    venv.uninstall_packages(package_name, was_injected=True)

    # inspect again: the uninstall can drop search path entries, such as an editable install's .pth
    if not leave_deps and (
        deps_of_uninstalled := _get_orphaned_dependencies(
            venv, canonicalize_name(package_name), requirements_before, _requirements_by_name(venv.python_path)
        )
    ):
        _LOGGER.info("Dependencies of uninstalled package: %s", deps_of_uninstalled)
        venv.uninstall_packages(*sorted(deps_of_uninstalled))

    if package.exposure.include_apps:
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
                    package=f"{package.package}{package.exposure.suffix}",
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


def _get_include_resource_paths(
    package: PackageInfo, venv: Venv, local_bin_dir: Path, local_man_dir: Path
) -> set[Path]:
    apps: Final[set[str]] = {
        name for app in package.apps_to_expose for name in exposed_app_names(app, package.exposure.suffix)
    }
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
                package, venv.man_path.parent / section, CTX.completion_dir / section
            )
            if f"{path.parent.parent.name}/{path.parent.name}/{path.name}" in completions
        }
    )


def _requirements_by_name(venv_python: Path) -> dict[str, set[str]]:
    venv_sys_path, venv_env, _ = fetch_info_in_venv(venv_python)
    return {
        name: get_required_dependency_names(distribution, venv_env)
        for name, distribution in get_distributions_by_name(venv_sys_path).items()
    }


def _get_orphaned_dependencies(
    venv: Venv, excluded_package: str, requirements_before: dict[str, set[str]], requirements_after: dict[str, set[str]]
) -> set[str]:
    pulled_in: Final[set[str]] = set()
    _collect_transitive_deps(excluded_package, requirements_before, pulled_in)
    # everything the package did not pull in stays, along with what it needs; the environment's own packages stay even
    # when the removed package was the one requiring them
    roots: Final[set[str]] = (requirements_after.keys() - pulled_in) | {
        canonicalize_name(name)
        for name in (venv.pipx_metadata.main_package.package, *venv.pipx_metadata.injected_packages)
        if name is not None
    }
    kept: Final[set[str]] = set()
    for root in roots:
        _collect_transitive_deps(root, requirements_after, kept)
    # walking reachability rather than counting dependents also frees dependencies that require each other
    return (pulled_in & requirements_after.keys()) - kept


def _collect_transitive_deps(package_name: str, requirements: dict[str, set[str]], visited: set[str]) -> None:
    if package_name in visited:
        return
    visited.add(package_name)
    for dependency_name in requirements.get(package_name, set()):
        _collect_transitive_deps(dependency_name, requirements, visited)


__all__ = [
    "uninject",
]
