import logging
import os
from pathlib import Path
from typing import List, Optional, Sequence

from pipx import commands, paths
from pipx.colors import bold, red
from pipx.commands.common import expose_resources_globally
from pipx.constants import EXIT_CODE_OK, ExitCode
from pipx.emojis import sleep
from pipx.package_specifier import parse_specifier_for_upgrade
from pipx.util import PipxError, pipx_wrap
from pipx.venv import Venv, VenvContainer

logger = logging.getLogger(__name__)


def _upgrade_package(
    venv: Venv,
    package_name: str,
    pip_args: List[str],
    is_main_package: bool,
    force: bool,
    upgrading_all: bool,
) -> int:
    """Returns 1 if package version changed, 0 if same version"""
    package_metadata = venv.package_metadata[package_name]

    if package_metadata.package_or_url is None:
        raise PipxError(f"Internal Error: package {package_name} has corrupt pipx metadata.")

    package_or_url = parse_specifier_for_upgrade(package_metadata.package_or_url)
    old_version = package_metadata.package_version

    venv.upgrade_package(
        package_name,
        package_or_url,
        pip_args,
        include_dependencies=package_metadata.include_dependencies,
        include_apps=package_metadata.include_apps,
        is_main_package=is_main_package,
        suffix=package_metadata.suffix,
    )

    package_metadata = venv.package_metadata[package_name]

    display_name = f"{package_metadata.package}{package_metadata.suffix}"
    new_version = package_metadata.package_version

    if package_metadata.include_apps:
        expose_resources_globally(
            "app",
            paths.ctx.bin_dir,
            package_metadata.app_paths,
            force=force,
            suffix=package_metadata.suffix,
        )
        expose_resources_globally("man", paths.ctx.man_dir, package_metadata.man_paths, force=force)

    if package_metadata.include_dependencies:
        for _, app_paths in package_metadata.app_paths_of_dependencies.items():
            expose_resources_globally(
                "app",
                paths.ctx.bin_dir,
                app_paths,
                force=force,
                suffix=package_metadata.suffix,
            )
        for _, man_paths in package_metadata.man_paths_of_dependencies.items():
            expose_resources_globally("man", paths.ctx.man_dir, man_paths, force=force)

    if old_version == new_version:
        if upgrading_all:
            pass
        else:
            print(
                pipx_wrap(
                    f"""
                    {display_name} is already at latest version {old_version}
                    (location: {str(venv.root)})
                    """
                )
            )
        return 0
    else:
        print(
            pipx_wrap(
                f"""
                upgraded package {display_name} from {old_version} to
                {new_version} (location: {str(venv.root)})
                """
            )
        )
        return 1


def _upgrade_venv(
    venv_dir: Path,
    pip_args: List[str],
    verbose: bool,
    *,
    include_injected: bool,
    upgrading_all: bool,
    force: bool,
    install: bool = False,
    python: Optional[str] = None,
) -> int:
    """Return number of packages with changed versions."""
    if not venv_dir.is_dir():
        if install:
            commands.install(
                venv_dir=None,
                venv_args=[],
                package_names=None,
                package_specs=[str(venv_dir).split(os.path.sep)[-1]],
                local_bin_dir=paths.ctx.bin_dir,
                local_man_dir=paths.ctx.man_dir,
                python=python,
                pip_args=pip_args,
                verbose=verbose,
                force=force,
                reinstall=False,
                include_dependencies=False,
                preinstall_packages=None,
            )
            return 0
        else:
            raise PipxError(
                f"""
                Package is not installed. Expected to find {str(venv_dir)}, but it
                does not exist.
                """
            )

    if python and not install:
        logger.info("Ignoring --python as not combined with --install")

    venv = Venv(venv_dir, verbose=verbose)
    venv.check_upgrade_shared_libs(pip_args=pip_args, verbose=verbose)

    if not venv.package_metadata:
        raise PipxError(
            f"Not upgrading {red(bold(venv_dir.name))}. It has missing internal pipx metadata.\n"
            f"It was likely installed using a pipx version before 0.15.0.0.\n"
            f"Please uninstall and install this package to fix.",
            wrap_message=False,
        )

    # Upgrade shared libraries (pip, setuptools and wheel)
    venv.upgrade_packaging_libraries(pip_args)

    versions_updated = 0

    package_name = venv.main_package_name
    versions_updated += _upgrade_package(
        venv,
        package_name,
        pip_args,
        is_main_package=True,
        force=force,
        upgrading_all=upgrading_all,
    )

    if include_injected:
        for package_name in venv.package_metadata:
            if package_name == venv.main_package_name:
                continue
            versions_updated += _upgrade_package(
                venv,
                package_name,
                pip_args,
                is_main_package=False,
                force=force,
                upgrading_all=upgrading_all,
            )

    return versions_updated


def upgrade(
    venv_dir: Path,
    python: Optional[str],
    pip_args: List[str],
    verbose: bool,
    *,
    include_injected: bool,
    force: bool,
    install: bool,
) -> ExitCode:
    """Return pipx exit code."""

    _ = _upgrade_venv(
        venv_dir,
        pip_args,
        verbose,
        include_injected=include_injected,
        upgrading_all=False,
        force=force,
        install=install,
        python=python,
    )

    # Any error in upgrade will raise PipxError (e.g. from venv.upgrade_package())
    return EXIT_CODE_OK


def upgrade_all(
    venv_container: VenvContainer,
    verbose: bool,
    *,
    pip_args: List[str],
    include_injected: bool,
    skip: Sequence[str],
    force: bool,
) -> ExitCode:
    """Returns pipx exit code."""
    venv_error = False
    venvs_upgraded = 0
    for venv_dir in venv_container.iter_venv_dirs():
        venv = Venv(venv_dir, verbose=verbose)
        venv.check_upgrade_shared_libs(pip_args=pip_args, verbose=verbose)
        if venv_dir.name in skip or "--editable" in venv.pipx_metadata.main_package.pip_args:
            continue
        try:
            venvs_upgraded += _upgrade_venv(
                venv_dir,
                venv.pipx_metadata.main_package.pip_args,
                verbose=verbose,
                include_injected=include_injected,
                upgrading_all=True,
                force=force,
            )

        except PipxError as e:
            venv_error = True
            logger.error(f"Error encountered when upgrading {venv_dir.name}:")
            logger.error(f"{e}\n")

    if venvs_upgraded == 0:
        print(f"Versions did not change after running 'pipx upgrade' for each package {sleep}")
    if venv_error:
        raise PipxError(
            "\nSome packages encountered errors during upgrade.\n" "    See specific error messages above.",
            wrap_message=False,
        )

    return EXIT_CODE_OK
