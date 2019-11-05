import logging
import shutil

from pathlib import Path
from shutil import which
from typing import List
from pipx.emojies import hazard

from pipx.util import WINDOWS, mkdir, rmdir


def _expose_apps_globally(
    local_bin_dir: Path, app_paths: List[Path], package: str, *, force: bool
):
    if WINDOWS:
        _copy_package_apps(local_bin_dir, app_paths, package)
    else:
        _symlink_package_apps(local_bin_dir, app_paths, package, force=force)


def _copy_package_apps(local_bin_dir: Path, app_paths: List[Path], package: str):
    for src_unresolved in app_paths:
        src = src_unresolved.resolve()
        app = src.name
        dest = Path(local_bin_dir / app)
        if not dest.parent.is_dir():
            mkdir(dest.parent)
        if dest.exists():
            logging.warning(f"{hazard}  Overwriting file {str(dest)} with {str(src)}")
            dest.unlink()
        if src.exists():
            shutil.copy(src, dest)


def _symlink_package_apps(
    local_bin_dir: Path, app_paths: List[Path], package: str, *, force: bool
):
    for app_path in app_paths:
        app_name = app_path.name
        symlink_path = Path(local_bin_dir / app_name)
        if not symlink_path.parent.is_dir():
            mkdir(symlink_path.parent)

        if force:
            logging.info(f"Force is true. Removing {str(symlink_path)}.")
            try:
                symlink_path.unlink()
            except FileNotFoundError:
                pass
            except IsADirectoryError:
                rmdir(symlink_path)

        exists = symlink_path.exists()
        is_symlink = symlink_path.is_symlink()
        if exists:
            if symlink_path.samefile(app_path):
                logging.info(f"Same path {str(symlink_path)} and {str(app_path)}")
            else:
                logging.warning(
                    f"{hazard}  File exists at {str(symlink_path)} and points "
                    f"to {symlink_path.resolve()}, not {str(app_path)}. Not modifying."
                )
            continue
        if is_symlink and not exists:
            logging.info(
                f"Removing existing symlink {str(symlink_path)} since it "
                "pointed non-existent location"
            )
            symlink_path.unlink()

        existing_executable_on_path = which(app_name)
        symlink_path.symlink_to(app_path)

        if existing_executable_on_path:
            logging.warning(
                f"{hazard}  Note: {app_name} was already on your PATH at "
                f"{existing_executable_on_path}"
            )
