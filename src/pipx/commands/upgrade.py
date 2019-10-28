import logging

from pathlib import Path
from typing import List


from pipx import constants
from pipx.constants import PIPX_PACKAGE_NAME
from pipx.emojies import sleep
from pipx.util import PipxError

from pipx.venv import Venv, VenvContainer
from .common import _expose_apps_globally


def upgrade(
    venv_dir: Path,
    package: str,
    package_or_url: str,
    pip_args: List[str],
    verbose: bool,
    *,
    upgrading_all: bool,
    include_dependencies: bool,
    force: bool,
) -> int:
    """Returns nonzero if package was upgraded, 0 if version did not change"""

    if not venv_dir.is_dir():
        raise PipxError(
            f"Package is not installed. Expected to find {str(venv_dir)}, "
            "but it does not exist."
        )

    venv = Venv(venv_dir, verbose=verbose)

    old_version = venv.get_venv_metadata_for_package(package).package_version

    # Upgrade shared libraries (pip, setuptools and wheel)
    venv.upgrade_packaging_libraries(pip_args)

    venv.upgrade_package(package_or_url, pip_args)
    new_version = venv.get_venv_metadata_for_package(package).package_version

    metadata = venv.get_venv_metadata_for_package(package)
    _expose_apps_globally(
        constants.LOCAL_BIN_DIR, metadata.app_paths, package, force=force
    )

    if include_dependencies:
        for _, app_paths in metadata.app_paths_of_dependencies.items():
            _expose_apps_globally(
                constants.LOCAL_BIN_DIR, app_paths, package, force=force
            )

    if old_version == new_version:
        if upgrading_all:
            pass
        else:
            print(
                f"{package} is already at latest version {old_version} (location: {str(venv_dir)})"
            )
        return 0
    else:
        print(
            f"upgraded package {package} from {old_version} to {new_version} (location: {str(venv_dir)})"
        )
        return 1


def upgrade_all(
    venv_container: VenvContainer,
    pip_args: List[str],
    verbose: bool,
    *,
    include_dependencies: bool,
    skip: List[str],
    force: bool,
):
    packages_upgraded = 0
    num_packages = 0
    for venv_dir in venv_container.iter_venv_dirs():
        num_packages += 1
        package = venv_dir.name
        if package in skip:
            continue
        if package == "pipx":
            package_or_url = PIPX_PACKAGE_NAME
        else:
            package_or_url = package
        try:
            packages_upgraded += upgrade(
                venv_dir,
                package,
                package_or_url,
                pip_args,
                verbose,
                upgrading_all=True,
                include_dependencies=include_dependencies,
                force=force,
            )
        except Exception:
            logging.error(f"Error encountered when upgrading {package}")

    if packages_upgraded == 0:
        print(
            f"Versions did not change after running 'pip upgrade' for each package {sleep}"
        )
