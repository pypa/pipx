import logging
from pathlib import Path
from typing import Sequence

from pipx.colors import bold
from pipx.constants import ExitCode
from pipx.emojis import sleep
from pipx.util import PipxError
from pipx.venv import Venv

logger = logging.getLogger(__name__)


def _update_pin_info(venv: Venv, package_name: str, is_main_package: bool, unpin: bool) -> int:
    package_metadata = venv.package_metadata[package_name]
    venv.update_package_metadata(
        package_name=str(package_metadata.package),
        package_or_url=str(package_metadata.package_or_url),
        pip_args=package_metadata.pip_args,
        include_dependencies=package_metadata.include_dependencies,
        include_apps=package_metadata.include_apps,
        is_main_package=is_main_package,
        suffix=package_metadata.suffix,
        pinned=not unpin,
    )
    return 1


def pin(
    venv_dir: Path,
    verbose: bool,
    skip: Sequence[str],
    injected_packages_only: bool = False,
) -> ExitCode:
    venv = Venv(venv_dir, verbose=verbose)
    try:
        main_package_metadata = venv.package_metadata[venv.main_package_name]
        if main_package_metadata.pinned:
            logger.warning(f"Package {main_package_metadata.package} already pinned {sleep}")
        elif skip and not injected_packages_only:
            raise PipxError("--skip must be used with --injected-packages-only")
        elif injected_packages_only:
            pinned_packages_count = 0
            pinned_packages_list = []
            for package_name in venv.package_metadata:
                if package_name == venv.main_package_name or package_name in skip:
                    continue

                if venv.package_metadata[package_name].pinned:
                    logger.warning(f"{package_name} was pinned. Not modifying.")
                    continue

                pinned_packages_count += _update_pin_info(venv, package_name, is_main_package=False, unpin=False)
                pinned_packages_list.append(package_name)

            if pinned_packages_count != 0:
                print(bold(f"Pinned {pinned_packages_count} packages in venv {venv.name}"))
                for package in pinned_packages_list:
                    print("  -", package)
        else:
            _update_pin_info(venv, venv.main_package_name, is_main_package=True, unpin=False)
    except KeyError as e:
        raise PipxError(f"Package {venv.name} is not installed") from e

    return ExitCode(0)


def unpin(venv_dir: Path, verbose: bool) -> ExitCode:
    venv = Venv(venv_dir, verbose=verbose)
    try:
        main_package_metadata = venv.package_metadata[venv.main_package_name]
        unpinned_packages_count = 0
        unpinned_packages_list = []
        for package_name in venv.package_metadata:
            if package_name == main_package_metadata.package and main_package_metadata.pinned:
                unpinned_packages_count += _update_pin_info(venv, package_name, is_main_package=True, unpin=True)
                unpinned_packages_list.append(package_name)
            elif venv.package_metadata[package_name].pinned:
                unpinned_packages_count += _update_pin_info(venv, package_name, is_main_package=False, unpin=True)
                unpinned_packages_list.append(package_name)

        if unpinned_packages_count != 0:
            print(bold(f"Unpinned {unpinned_packages_count} packages in venv {venv.name}"))
            for package in unpinned_packages_list:
                print("  -", package)
        else:
            logger.warning(f"No packages to unpin in venv {venv.name}")
    except KeyError as e:
        raise PipxError(f"Package {venv.name} is not installed") from e

    return ExitCode(0)
