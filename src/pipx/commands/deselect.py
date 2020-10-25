from pipx import constants
from pipx.colors import red, bold
from pipx.commands.common import (
    find_selected_venvs_for_package,
    expose_package_globally,
    unexpose_package_globally,
)
from pipx.util import PipxError
from pipx.venv import VenvContainer, Venv


def deselect(
    package_name: str, verbose: bool,
):
    venv_container = VenvContainer(constants.PIPX_LOCAL_VENVS)
    venv_dir = venv_container.get_venv_dir(package_name)

    if venv_dir.is_dir():
        # package_name is package name plus suffix
        venv = Venv(venv_dir, verbose=verbose)
    else:
        # package_name is bare package name
        selected_venvs = find_selected_venvs_for_package(
            venv_container, package_name, verbose=verbose
        )
        if len(selected_venvs) == 0:
            raise PipxError(
                f"No package with suffix selected for package {package_name}."
            )

        venv = selected_venvs[0]

    if not venv.package_metadata:
        print(
            f"Not deselecting {red(bold(venv.main_package_name))}.  It has missing internal pipx metadata.\n"
            f"    It was likely installed using a pipx version before 0.15.0.0.\n"
            f"    Please uninstall and install this package, or reinstall-all to fix."
        )
        return 1

    package_metadata = venv.package_metadata[venv.main_package_name]
    print(
        f"Deselecting apps from venv '{venv.root.name}' for package '{package_metadata.package}':"
    )

    # mark package as not selected
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

    # remove all links to venv and the recreate those with suffix
    unexpose_package_globally(constants.LOCAL_BIN_DIR, package_metadata)
    expose_package_globally(
        constants.LOCAL_BIN_DIR,
        package_metadata,
        force=True,
        suffix=package_metadata.suffix,
    )

    removed_links = package_metadata.apps.copy()
    if package_metadata.include_apps:
        removed_links.extend(package_metadata.apps_of_dependencies)

    for app in removed_links:
        print(f"  - unlinked {app}")
