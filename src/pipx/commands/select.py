from pipx import constants
from pipx.commands.common import expose_apps_globally
from pipx.pipx_metadata_file import PackageInfo
from pipx.util import PipxError
from pipx.venv import VenvContainer, Venv


def select(
    package_name_with_suffix: str,
    include_dependencies: bool,
    verbose: bool,
):
    venv_container = VenvContainer(constants.PIPX_LOCAL_VENVS)
    venv_dir = venv_container.get_venv_dir(package_name_with_suffix)
    venv = Venv(venv_dir, verbose=verbose)

    # check package with suffix exists
    if not venv_dir.is_dir():
        raise PipxError(f"Package and suffix '{package_name_with_suffix}' are not installed.")

    package_info = venv.package_metadata[venv.main_package_name]

    # check package without suffix does not exist
    venv_non_suffix = venv_container.get_venv_dir(package_info.package)
    if venv_non_suffix.is_dir():
        raise PipxError(f"Package '{package_info.package}' is already installed without suffix.")

    print(f"Selecting apps from venv '{package_name_with_suffix}' for package '{package_info.package}':")

    # create links to binaries
    expose_apps_globally(
        constants.LOCAL_BIN_DIR,
        package_info.app_paths,
        force=True,
    )

    for app in package_info.apps:
        print(f'  - {app}{package_info.suffix} is now also {app}')

    if include_dependencies:
        for _, app_paths in package_info.app_paths_of_dependencies.items():
            expose_apps_globally(
                constants.LOCAL_BIN_DIR,
                package_info.app_paths,
                force=True,
            )

        for app in package_info.apps_of_dependencies:
            print(f'  - {app}{package_info.suffix} is now also {app}')
