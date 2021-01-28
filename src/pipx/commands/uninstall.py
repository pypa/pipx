import logging
from pathlib import Path
from shutil import which
from typing import List

from pipx import constants
from pipx.constants import (
    EXIT_CODE_OK,
    EXIT_CODE_UNINSTALL_ERROR,
    EXIT_CODE_UNINSTALL_VENV_NONEXISTENT,
    WINDOWS,
    ExitCode,
)
from pipx.emojis import hazard, sleep, stars
from pipx.util import rmdir
from pipx.venv import Venv, VenvContainer

logger = logging.getLogger(__name__)


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

    if venv.pipx_metadata.main_package is not None:
        app_paths: List[Path] = []
        for viewed_package in venv.package_metadata.values():
            app_paths += viewed_package.app_paths
            for dep_paths in viewed_package.app_paths_of_dependencies.values():
                app_paths += dep_paths
    else:
        # fallback if not metadata from pipx_metadata.json
        if venv.python_path.is_file():
            # has a valid python interpreter and can get metadata about the package
            # In pre-metadata-pipx venv_dir.name is name of main package
            metadata = venv.get_venv_metadata_for_package(venv_dir.name)
            app_paths = metadata.app_paths
            for dep_paths in metadata.app_paths_of_dependencies.values():
                app_paths += dep_paths
        else:
            # Doesn't have a valid python interpreter. We'll take our best guess on what to uninstall
            # here based on symlink location. pipx doesn't use symlinks on windows, so this is for
            # non-windows only.
            # The heuristic here is any symlink in ~/.local/bin pointing to .local/pipx/venvs/VENV_NAME/bin
            # should be uninstalled.
            if WINDOWS:
                app_paths = []
            else:
                apps_linking_to_venv_bin_dir = [
                    f
                    for f in constants.LOCAL_BIN_DIR.iterdir()
                    if str(f.resolve()).startswith(str(venv.bin_path))
                ]
                app_paths = apps_linking_to_venv_bin_dir

    for filepath in local_bin_dir.iterdir():
        if WINDOWS:
            for b in app_paths:
                if filepath.exists() and filepath.name == b.name:
                    filepath.unlink()
        else:
            symlink = filepath
            for b in app_paths:
                if symlink.exists() and b.exists() and symlink.samefile(b):
                    logger.info(f"removing symlink {str(symlink)}")
                    symlink.unlink()

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
