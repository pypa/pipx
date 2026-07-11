import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from pipx.colors import bold
from pipx.constants import ExitCode
from pipx.emojis import sleep
from pipx.util import PipxError
from pipx.venv import Venv

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def _update_pin_info(venv: Venv, package_name: str, is_main_package: bool, unpin: bool) -> None:
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


def pin(
    venv_dir: Path,
    verbose: bool,
    skip: Sequence[str],
    injected_only: bool = False,
) -> ExitCode:
    venv = Venv(venv_dir, verbose=verbose)
    try:
        main_package_metadata = venv.package_metadata[venv.main_package_name]
    except KeyError as e:
        raise PipxError(f"Package {venv.name} is not installed") from e

    if injected_only or skip:
        pinned_packages_list: list[str] = []
        for package_name in venv.package_metadata:
            if package_name == venv.main_package_name or package_name in skip:
                continue

            if venv.package_metadata[package_name].pinned:
                print(f"{package_name} was pinned. Not modifying.")
                continue

            _update_pin_info(venv, package_name, is_main_package=False, unpin=False)
            pinned_packages_list.append(f"{package_name} {venv.package_metadata[package_name].package_version}")

        if pinned_packages_list:
            print(bold(f"Pinned {len(pinned_packages_list)} packages in venv {venv.name}"))
            for package in pinned_packages_list:
                print("  -", package)
    elif main_package_metadata.pinned:
        _LOGGER.warning(f"Package {main_package_metadata.package} already pinned {sleep}")
    else:
        for package_name in venv.package_metadata:
            if package_name == venv.main_package_name:
                _update_pin_info(venv, venv.main_package_name, is_main_package=True, unpin=False)
            else:
                _update_pin_info(venv, package_name, is_main_package=False, unpin=False)

    return ExitCode(0)


def unpin(venv_dir: Path, verbose: bool) -> ExitCode:
    venv = Venv(venv_dir, verbose=verbose)
    try:
        main_package_metadata = venv.package_metadata[venv.main_package_name]
    except KeyError as e:
        raise PipxError(f"Package {venv.name} is not installed") from e

    unpinned_packages_list: list[str] = []

    for package_name in venv.package_metadata:
        if not venv.package_metadata[package_name].pinned:
            continue
        _update_pin_info(
            venv,
            package_name,
            is_main_package=package_name == main_package_metadata.package,
            unpin=True,
        )
        unpinned_packages_list.append(package_name)

    if unpinned_packages_list:
        print(bold(f"Unpinned {len(unpinned_packages_list)} packages in venv {venv.name}"))
        for package in unpinned_packages_list:
            print("  -", package)
    else:
        _LOGGER.warning(f"No packages to unpin in venv {venv.name}")

    return ExitCode(0)


__all__ = [
    "pin",
    "unpin",
]
