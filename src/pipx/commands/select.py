from pipx import constants
from pipx.commands.common import expose_apps_globally
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

    if not venv_dir.is_dir():
        raise PipxError(f"Package and suffix {package_name_with_suffix} are not installed.")

    package_metadata = venv.get_package_metadata(None)
    package = package_metadata.package

    expose_apps_globally(
        constants.LOCAL_BIN_DIR,
        package_metadata.app_paths,
        package,
        force=True,
    )

    if include_dependencies:
        for _, app_paths in package_metadata.app_paths_of_dependencies.items():
            expose_apps_globally(
                constants.LOCAL_BIN_DIR,
                app_paths,
                package,
                force=True,
            )
