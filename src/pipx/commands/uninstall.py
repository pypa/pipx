import logging
from pathlib import Path
from shutil import which
from typing import List
from pipx.util import WINDOWS, rmdir


from pipx import constants
from pipx.emojies import hazard, stars, sleep
from pipx.venv import Venv, VenvContainer


def uninstall(venv_dir: Path, package: str, local_bin_dir: Path, verbose: bool):
    """Uninstall entire venv_dir, including main package and all injected
    packages.
    """
    if not venv_dir.exists():
        print(f"Nothing to uninstall for {package} {sleep}")
        app = which(package)
        if app:
            print(
                f"{hazard}  Note: '{app}' still exists on your system and is on your PATH"
            )
        return

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
            metadata = venv.get_venv_metadata_for_package(package)
            app_paths = metadata.app_paths
            for dep_paths in metadata.app_paths_of_dependencies.values():
                app_paths += dep_paths
        else:
            # Doesn't have a valid python interpreter. We'll take our best guess on what to uninstall
            # here based on symlink location. pipx doesn't use symlinks on windows, so this is for
            # non-windows only.
            # The heuristic here is any symlink in ~/.local/bin pointing to .local/pipx/venvs/PACKAGE/bin
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

    for file in local_bin_dir.iterdir():
        if WINDOWS:
            for b in app_paths:
                if file.name == b.name:
                    file.unlink()
        else:
            symlink = file
            for b in app_paths:
                if symlink.exists() and b.exists() and symlink.samefile(b):
                    logging.info(f"removing symlink {str(symlink)}")
                    symlink.unlink()

    rmdir(venv_dir)
    print(f"uninstalled {package}! {stars}")


def uninstall_all(venv_container: VenvContainer, local_bin_dir: Path, verbose: bool):
    for venv_dir in venv_container.iter_venv_dirs():
        package = venv_dir.name
        uninstall(venv_dir, package, local_bin_dir, verbose)
