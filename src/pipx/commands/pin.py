import logging
from pathlib import Path

from pipx.constants import ExitCode
from pipx.emojis import sleep
from pipx.util import PipxError
from pipx.venv import Venv

logger = logging.getLogger(__name__)


def pin(venv_dir: Path, verbose: bool, unpin: bool = False) -> ExitCode:
    venv = Venv(venv_dir, verbose=verbose)
    try:
        package_metadata = venv.package_metadata[venv.main_package_name]
        if package_metadata.pinned and not unpin:
            logger.warning(f"Package {package_metadata.package} already pinned {sleep}")
        elif not package_metadata.pinned and unpin:
            logger.warning(f"Package {package_metadata.package} not pinned {sleep}")
        else:
            venv.update_package_metadata(
                package_name=str(package_metadata.package),
                package_or_url=str(package_metadata.package_or_url),
                pip_args=package_metadata.pip_args,
                include_dependencies=package_metadata.include_dependencies,
                include_apps=package_metadata.include_apps,
                is_main_package=True,
                suffix=package_metadata.suffix,
                pinned=False if unpin else True,
            )
    except KeyError as e:
        raise PipxError(f"Package {venv.name} is not installed") from e

    return ExitCode(0)
