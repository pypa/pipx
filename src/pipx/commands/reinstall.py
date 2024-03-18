import sys
from pathlib import Path
from typing import List, Sequence

from packaging.utils import canonicalize_name

from pipx.commands.inject import inject_dep
from pipx.commands.install import install
from pipx.commands.uninstall import uninstall
from pipx.constants import (
    EXIT_CODE_OK,
    EXIT_CODE_REINSTALL_INVALID_PYTHON,
    EXIT_CODE_REINSTALL_VENV_NONEXISTENT,
    ExitCode,
)
from pipx.emojis import error, sleep
from pipx.util import PipxError
from pipx.venv import Venv, VenvContainer


def reinstall(
    *,
    venv_dir: Path,
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str,
    verbose: bool,
    force_reinstall_shared_libs: bool = False,
) -> ExitCode:
    """Returns pipx exit code."""
    if not venv_dir.exists():
        print(f"Nothing to reinstall for {venv_dir.name} {sleep}")
        return EXIT_CODE_REINSTALL_VENV_NONEXISTENT

    try:
        Path(python).relative_to(venv_dir)
    except ValueError:
        pass
    else:
        print(
            f"{error} Error, the python executable would be deleted!",
            "Change it using the --python option or PIPX_DEFAULT_PYTHON environment variable.",
        )
        return EXIT_CODE_REINSTALL_INVALID_PYTHON

    venv = Venv(venv_dir, verbose=verbose)
    venv.check_upgrade_shared_libs(
        pip_args=venv.pipx_metadata.main_package.pip_args, verbose=verbose, force_upgrade=force_reinstall_shared_libs
    )

    if venv.pipx_metadata.main_package.package_or_url is not None:
        package_or_url = venv.pipx_metadata.main_package.package_or_url
    else:
        package_or_url = venv.main_package_name

    uninstall(venv_dir, local_bin_dir, local_man_dir, verbose)

    # in case legacy original dir name
    venv_dir = venv_dir.with_name(canonicalize_name(venv_dir.name))

    # install main package first
    install(
        venv_dir,
        [venv.main_package_name],
        [package_or_url],
        local_bin_dir,
        local_man_dir,
        python,
        venv.pipx_metadata.main_package.pip_args,
        venv.pipx_metadata.venv_args,
        verbose,
        force=True,
        reinstall=True,
        include_dependencies=venv.pipx_metadata.main_package.include_dependencies,
        preinstall_packages=[],
        suffix=venv.pipx_metadata.main_package.suffix,
    )

    # now install injected packages
    for injected_name, injected_package in venv.pipx_metadata.injected_packages.items():
        if injected_package.package_or_url is None:
            # This should never happen, but package_or_url is type
            #   Optional[str] so mypy thinks it could be None
            raise PipxError(f"Internal Error injecting package {injected_package} into {venv.name}")
        inject_dep(
            venv_dir,
            injected_name,
            injected_package.package_or_url,
            injected_package.pip_args,
            verbose=verbose,
            include_apps=injected_package.include_apps,
            include_dependencies=injected_package.include_dependencies,
            force=True,
        )

    # Any failure to install will raise PipxError, otherwise success
    return EXIT_CODE_OK


def reinstall_all(
    venv_container: VenvContainer,
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str,
    verbose: bool,
    *,
    skip: Sequence[str],
) -> ExitCode:
    """Returns pipx exit code."""
    failed: List[str] = []

    # iterate on all packages and reinstall them
    # for the first one, we also trigger
    # a reinstall of shared libs beforehand
    first_reinstall = True
    for venv_dir in venv_container.iter_venv_dirs():
        if venv_dir.name in skip:
            continue
        try:
            package_exit = reinstall(
                venv_dir=venv_dir,
                local_bin_dir=local_bin_dir,
                local_man_dir=local_man_dir,
                python=python,
                verbose=verbose,
                force_reinstall_shared_libs=first_reinstall,
            )
        except PipxError as e:
            print(e, file=sys.stderr)
            failed.append(venv_dir.name)
        else:
            first_reinstall = False
            if package_exit != 0:
                failed.append(venv_dir.name)
    if len(failed) > 0:
        raise PipxError(f"The following package(s) failed to reinstall: {', '.join(failed)}")
    # Any failure to install will raise PipxError, otherwise success
    return EXIT_CODE_OK
