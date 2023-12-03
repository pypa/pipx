import logging
from collections.abc import Callable
from pathlib import Path
from shutil import which
from typing import List, Optional, Set

from pipx.commands.common import (
    add_suffix,
    can_symlink,
    get_exposed_man_paths_for_package,
    get_exposed_paths_for_package,
)
from pipx.constants import (
    EXIT_CODE_OK,
    EXIT_CODE_UNINSTALL_ERROR,
    EXIT_CODE_UNINSTALL_VENV_NONEXISTENT,
    MAN_SECTIONS,
    ExitCode,
)
from pipx.emojis import hazard, sleep, stars
from pipx.pipx_metadata_file import PackageInfo
from pipx.util import rmdir, safe_unlink
from pipx.venv import Venv, VenvContainer
from pipx.venv_inspect import VenvMetadata

logger = logging.getLogger(__name__)


def _venv_metadata_to_package_info(
    venv_metadata: VenvMetadata,
    package_name: str,
    package_or_url: str = "",
    pip_args: Optional[List[str]] = None,
    include_apps: bool = True,
    include_dependencies: bool = False,
    suffix: str = "",
) -> PackageInfo:
    if pip_args is None:
        pip_args = []

    return PackageInfo(
        package=package_name,
        package_or_url=package_or_url,
        pip_args=pip_args,
        include_apps=include_apps,
        include_dependencies=include_dependencies,
        apps=venv_metadata.apps,
        app_paths=venv_metadata.app_paths,
        apps_of_dependencies=venv_metadata.apps_of_dependencies,
        app_paths_of_dependencies=venv_metadata.app_paths_of_dependencies,
        man_pages=venv_metadata.man_pages,
        man_paths=venv_metadata.man_paths,
        man_pages_of_dependencies=venv_metadata.man_pages_of_dependencies,
        man_paths_of_dependencies=venv_metadata.man_paths_of_dependencies,
        package_version=venv_metadata.package_version,
        suffix=suffix,
    )


def _get_package_bin_dir_app_paths(
    venv: Venv, package_info: PackageInfo, venv_bin_path: Path, local_bin_dir: Path
) -> Set[Path]:
    suffix = package_info.suffix
    apps = []
    if package_info.include_apps:
        apps += package_info.apps
    if package_info.include_dependencies:
        apps += package_info.apps_of_dependencies
    return get_exposed_paths_for_package(venv_bin_path, local_bin_dir, [add_suffix(app, suffix) for app in apps])


def _get_package_man_paths(venv: Venv, package_info: PackageInfo, venv_man_path: Path, local_man_dir: Path) -> Set[Path]:
    man_pages = []
    if package_info.include_apps:
        man_pages += package_info.man_pages
    if package_info.include_dependencies:
        man_pages += package_info.man_pages_of_dependencies
    return get_exposed_man_paths_for_package(venv_man_path, local_man_dir, man_pages)


def _get_venv_resource_paths(
    resource_type: str, venv: Venv, venv_resource_path: Path, local_resource_dir: Path
) -> Set[Path]:
    resource_paths = set()
    assert resource_type in ("app", "man"), "invalid resource type"
    get_package_resource_paths: Callable[[Venv, PackageInfo, Path, Path], Set[Path]]
    get_package_resource_paths = {
        "app": _get_package_bin_dir_app_paths,
        "man": _get_package_man_paths,
    }[resource_type]

    if venv.pipx_metadata.main_package.package is not None:
        # Valid metadata for venv
        for package_info in venv.package_metadata.values():
            resource_paths |= get_package_resource_paths(venv, package_info, venv_resource_path, local_resource_dir)
    elif venv.python_path.is_file():
        # No metadata from pipx_metadata.json, but valid python interpreter.
        # In pre-metadata-pipx venv.root.name is name of main package
        # In pre-metadata-pipx there is no suffix
        # We make the conservative assumptions: no injected packages,
        # not include_dependencies.  Other PackageInfo fields are irrelevant
        # here.
        venv_metadata = venv.get_venv_metadata_for_package(venv.root.name, set())
        main_package_info = _venv_metadata_to_package_info(venv_metadata, venv.root.name)
        resource_paths = get_package_resource_paths(venv, main_package_info, venv_resource_path, local_resource_dir)
    else:
        # No metadata and no valid python interpreter.
        # We'll take our best guess on what to uninstall here based on symlink
        # location for symlink-capable systems.
        # The heuristic here is any symlink in ~/.local/bin pointing to
        # .local/share/pipx/venvs/VENV_NAME/{bin,Scripts} should be uninstalled.

        # For non-symlink systems we give up and return an empty set.
        if not local_resource_dir.is_dir() or not can_symlink(local_resource_dir):
            return set()

        resource_paths = get_exposed_paths_for_package(venv_resource_path, local_resource_dir)

    return resource_paths


def uninstall(venv_dir: Path, local_bin_dir: Path, local_man_dir: Path, verbose: bool) -> ExitCode:
    """Uninstall entire venv_dir, including main package and all injected
    packages.

    Returns pipx exit code.
    """
    if not venv_dir.exists():
        print(f"Nothing to uninstall for {venv_dir.name} {sleep}")
        app = which(venv_dir.name)
        if app:
            print(f"{hazard}  Note: '{app}' still exists on your system and is on your PATH")
        return EXIT_CODE_UNINSTALL_VENV_NONEXISTENT

    venv = Venv(venv_dir, verbose=verbose)

    bin_dir_app_paths = _get_venv_resource_paths("app", venv, venv.bin_path, local_bin_dir)
    man_dir_paths = set()
    for man_section in MAN_SECTIONS:
        man_dir_paths |= _get_venv_resource_paths("man", venv, venv.man_path / man_section, local_man_dir / man_section)

    for path in bin_dir_app_paths | man_dir_paths:
        try:
            safe_unlink(path)
        except FileNotFoundError:
            logger.info(f"tried to remove but couldn't find {path}")
        else:
            logger.info(f"removed file {path}")

    rmdir(venv_dir)
    print(f"uninstalled {venv.name}! {stars}")
    return EXIT_CODE_OK


def uninstall_all(
    venv_container: VenvContainer,
    local_bin_dir: Path,
    local_man_dir: Path,
    verbose: bool,
) -> ExitCode:
    """Returns pipx exit code."""
    all_success = True
    for venv_dir in venv_container.iter_venv_dirs():
        return_val = uninstall(venv_dir, local_bin_dir, local_man_dir, verbose)
        all_success &= return_val == 0

    return EXIT_CODE_OK if all_success else EXIT_CODE_UNINSTALL_ERROR
