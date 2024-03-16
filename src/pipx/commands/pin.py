from pathlib import Path

from pipx.constants import ExitCode
from pipx.venv import Venv

def pin(venv_dir: Path, verbose: bool, unpin: bool) -> ExitCode:
    venv = Venv(venv_dir, verbose=verbose)
    package_metadata = venv.package_metadata[venv.main_package_name]
    venv.update_package_metadata(
        package_name=package_metadata.package,
        package_or_url=package_metadata.package_or_url,
        pip_args=package_metadata.pip_args,
        include_dependencies=package_metadata.include_dependencies,
        include_apps=package_metadata.include_apps,
        is_main_package=True,
        suffix=package_metadata.suffix,
        pinned=False if unpin else True,
    )
    return ExitCode(0)

