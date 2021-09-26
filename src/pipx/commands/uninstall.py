import logging
from pathlib import Path
from shutil import which
from typing import List, Optional, Set

from pipx.commands.common import (
    add_suffix,
    can_symlink,
    get_exposed_app_paths_for_package,
)
from pipx.constants import (
    EXIT_CODE_OK,
    EXIT_CODE_UNINSTALL_ERROR,
    EXIT_CODE_UNINSTALL_VENV_NONEXISTENT,
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
        package_version=venv_metadata.package_version,
        suffix=suffix,
    )


def _get_package_bin_dir_app_paths(
    venv: Venv, package_info: PackageInfo, local_bin_dir: Path
) -> Set[Path]:
    suffix = package_info.suffix
    apps = []
    if package_info.include_apps:
        apps += package_info.apps
    if package_info.include_dependencies:
        apps += package_info.apps_of_dependencies
    return get_exposed_app_paths_for_package(
        venv.bin_path, local_bin_dir, [add_suffix(app, suffix) for app in apps]
    )


def _get_venv_bin_dir_app_paths(venv: Venv, local_bin_dir: Path) -> Set[Path]:
    bin_dir_app_paths = set()
    if venv.pipx_metadata.main_package.package is not None:
        # Valid metadata for venv
        for package_info in venv.package_metadata.values():
            bin_dir_app_paths |= _get_package_bin_dir_app_paths(
                venv, package_info, local_bin_dir
            )
    elif venv.python_path.is_file():
        # No metadata from pipx_metadata.json, but valid python interpreter.
        # In pre-metadata-pipx venv.root.name is name of main package
        # In pre-metadata-pipx there is no suffix
        # We make the conservative assumptions: no injected packages,
        # not include_dependencies.  Other PackageInfo fields are irrelevant
        # here.
        venv_metadata = venv.get_venv_metadata_for_package(venv.root.name, set())
        main_package_info = _venv_metadata_to_package_info(
            venv_metadata, venv.root.name
        )
        bin_dir_app_paths = _get_package_bin_dir_app_paths(
            venv, main_package_info, local_bin_dir
        )
    else:
        # No metadata and no valid python interpreter.
        # We'll take our best guess on what to uninstall here based on symlink
        # location for symlink-capable systems.
        # The heuristic here is any symlink in ~/.local/bin pointing to
        # .local/pipx/venvs/VENV_NAME/{bin,Scripts} should be uninstalled.

        # For non-symlink systems we give up and return and empty set.
        if not can_symlink(local_bin_dir):
            return set()

        bin_dir_app_paths = get_exposed_app_paths_for_package(
            venv.bin_path, local_bin_dir
        )

    return bin_dir_app_paths


def uninstall(venv_dir: Path, local_bin_dir: Path, verbose: bool) -> ExitCode:
    """Uninstall entire venv_dir, including main package and all injected
    packages.

    Returns pipx exit code.
    """
    if not venv_dir.exists():
        print(f"Nothing to uninstall for {venv_dir.name} {sleep}")
        app = which(venv_dir.name)
        if app:
            print(
                f"{hazard}  Note: '{app}' still exists on your system and is on your PATH"
            )
        return EXIT_CODE_UNINSTALL_VENV_NONEXISTENT

    venv = Venv(venv_dir, verbose=verbose)

    bin_dir_app_paths = _get_venv_bin_dir_app_paths(venv, local_bin_dir)

    for bin_dir_app_path in bin_dir_app_paths:
        try:
            safe_unlink(bin_dir_app_path)
        except FileNotFoundError:
            logger.info(f"tried to remove but couldn't find {bin_dir_app_path}")
        else:
            logger.info(f"removed file {bin_dir_app_path}")

    rmdir(venv_dir)
    print(f"uninstalled {venv.name}! {stars}")
    return EXIT_CODE_OK


def uninstall_all(
    venv_container: VenvContainer, local_bin_dir: Path, verbose: bool
) -> ExitCode:
    """Returns pipx exit code."""
    all_success = True
    for venv_dir in venv_container.iter_venv_dirs():
        return_val = uninstall(venv_dir, local_bin_dir, verbose)
        all_success &= return_val == 0

    return EXIT_CODE_OK if all_success else EXIT_CODE_UNINSTALL_ERROR
