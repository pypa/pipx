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

    old_package_metadata = venv.package_metadata[package]
    old_version = old_package_metadata.package_version

    # if default package_or_url, check pipx_metadata for better url
    # TODO 20190926: main.py should communicate if this is spec or copied from
    #   package
    if package_or_url == package:
        if venv.pipx_metadata.main_package.package_or_url is not None:
            package_or_url = venv.pipx_metadata.main_package.package_or_url
        else:
            package_or_url = package

    # Upgrade shared libraries (pip, setuptools and wheel)
    venv.upgrade_packaging_libraries(pip_args)

    venv.upgrade_package(
        package,
        package_or_url,
        pip_args,
        # TODO 20191026: should this be `include_dependencies`?
        include_dependencies=old_package_metadata.include_dependencies,
        include_apps=old_package_metadata.include_apps,
        is_main_package=True,
    )
    # TODO 20191026: Should we upgrade injected packages also?

    package_metadata = venv.package_metadata[package]
    new_version = package_metadata.package_version

    _expose_apps_globally(
        constants.LOCAL_BIN_DIR, package_metadata.app_paths, package, force=force
    )

    if include_dependencies:
        for _, app_paths in package_metadata.app_paths_of_dependencies.items():
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
    venv_container: VenvContainer, verbose: bool, *, skip: List[str], force: bool
):
    packages_upgraded = 0
    num_packages = 0
    for venv_dir in venv_container.iter_venv_dirs():
        num_packages += 1
        package = venv_dir.name
        venv = Venv(venv_dir, verbose=verbose)
        if package in skip:
            continue
        if package == "pipx":
            package_or_url = PIPX_PACKAGE_NAME
        else:
            if venv.pipx_metadata.main_package.package_or_url is not None:
                package_or_url = venv.pipx_metadata.main_package.package_or_url
            else:
                package_or_url = package
        try:
            packages_upgraded += upgrade(
                venv_dir,
                package,
                package_or_url,
                venv.pipx_metadata.main_package.pip_args,
                verbose,
                upgrading_all=True,
                include_dependencies=venv.pipx_metadata.main_package.include_dependencies,
                force=force,
            )
        # TODO 20191024: Upgrade injected packages

        except Exception:
            logging.error(f"Error encountered when upgrading {package}")

    if packages_upgraded == 0:
        print(
            f"Versions did not change after running 'pip upgrade' for each package {sleep}"
        )
