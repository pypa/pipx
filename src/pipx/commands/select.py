from pipx import constants
from pipx.colors import red, bold
from pipx.commands.common import (
    find_selected_venvs_for_package,
    expose_package_globally,
    unexpose_package_globally,
)
from pipx.util import PipxError
from pipx.venv import VenvContainer, Venv


def select(
    package_name_with_suffix: str, verbose: bool,
):
    venv_container = VenvContainer(constants.PIPX_LOCAL_VENVS)
    venv_dir = venv_container.get_venv_dir(package_name_with_suffix)

    # check package with suffix exists
    if not venv_dir.is_dir():
        raise PipxError(
            f"Package and suffix '{package_name_with_suffix}' are not installed."
        )

    venv = Venv(venv_dir, verbose=verbose)
    if not venv.package_metadata:
        print(
            f"Not selecting {red(bold(venv.main_package_name))}.  It has missing internal pipx metadata.\n"
            f"    It was likely installed using a pipx version before 0.15.0.0.\n"
            f"    Please uninstall and install this package, or reinstall-all to fix."
        )
        return 1
    package_metadata = venv.package_metadata[venv.main_package_name]

    # check if we are trying to select a non-suffixed version
    if package_name_with_suffix == package_metadata.package:
        raise PipxError(
            f"Cannot select '{package_name_with_suffix}' as it already has no suffix."
        )

    # check package without suffix does not exist
    venv_non_suffix = venv_container.get_venv_dir(package_metadata.package)
    if venv_non_suffix.is_dir():
        raise PipxError(
            f"Package '{package_metadata.package}' is already installed without suffix."
        )

    print(
        f"Selecting apps from venv '{package_name_with_suffix}' for package '{package_metadata.package}':"
    )

    # deselect other package if selected
    selected_venvs = find_selected_venvs_for_package(
        venv_container, package_metadata.package, verbose=verbose
    )
    for selected_venv in selected_venvs:
        selected_package_metadata = selected_venv.package_metadata[
            selected_venv.main_package_name
        ]

        # mark package as not selected
        selected_venv.update_package_metadata(
            package=selected_package_metadata.package,
            package_or_url=selected_package_metadata.package_or_url,
            pip_args=selected_package_metadata.pip_args,
            include_dependencies=selected_package_metadata.include_dependencies,
            include_apps=selected_package_metadata.include_apps,
            is_main_package=True,
            suffix=selected_package_metadata.suffix,
            selected_as_default=False,
        )

        # remove links of previously selected package
        unexpose_package_globally(constants.LOCAL_BIN_DIR, selected_package_metadata)

    # mark package as selected
    venv.update_package_metadata(
        package=package_metadata.package,
        package_or_url=package_metadata.package_or_url,
        pip_args=package_metadata.pip_args,
        include_dependencies=package_metadata.include_dependencies,
        include_apps=package_metadata.include_apps,
        is_main_package=True,
        suffix=package_metadata.suffix,
        selected_as_default=True,
    )

    # create links to binaries
    expose_package_globally(
        constants.LOCAL_BIN_DIR, package_metadata, force=True, suffix="",
    )

    created_links = package_metadata.apps.copy()
    if package_metadata.include_apps:
        created_links.extend(package_metadata.apps_of_dependencies)

    for app in created_links:
        print(f"  - {app}{package_metadata.suffix} is now linked as {app}")
