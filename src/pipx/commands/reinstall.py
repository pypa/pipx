from pathlib import Path
from typing import List
import sys

from pipx.commands.inject import inject
from pipx.commands.install import install
from pipx.commands.uninstall import uninstall
from pipx.util import PipxError
from pipx.venv import Venv, VenvContainer


def reinstall(
    *, venv_dir: Path, package: str, local_bin_dir: Path, python: str, verbose: bool,
):
    venv = Venv(venv_dir, verbose=verbose)

    if venv.pipx_metadata.main_package.package_or_url is not None:
        package_or_url = venv.pipx_metadata.main_package.package_or_url
    else:
        package_or_url = package

    uninstall(venv_dir, package, local_bin_dir, verbose)

    # install main package first
    install(
        venv_dir,
        package,
        package_or_url,
        local_bin_dir,
        python,
        venv.pipx_metadata.main_package.pip_args,
        venv.pipx_metadata.venv_args,
        verbose,
        force=True,
        include_dependencies=venv.pipx_metadata.main_package.include_dependencies,
    )

    # now install injected packages
    for (
        injected_name,
        injected_package,
    ) in venv.pipx_metadata.injected_packages.items():
        if injected_package.package_or_url is None:
            # This should never happen, but package_or_url is type
            #   Optional[str] so mypy thinks it could be None
            raise PipxError(
                f"Internal Error injecting package {injected_package} into {package}"
            )
        inject(
            venv_dir,
            injected_name,
            injected_package.package_or_url,
            injected_package.pip_args,
            verbose=verbose,
            include_apps=injected_package.include_apps,
            include_dependencies=injected_package.include_dependencies,
            force=True,
        )


def reinstall_all(
    venv_container: VenvContainer,
    local_bin_dir: Path,
    python: str,
    verbose: bool,
    *,
    skip: List[str],
):
    failed: List[str] = []
    for venv_dir in venv_container.iter_venv_dirs():
        package = venv_dir.name
        if package in skip:
            continue
        try:
            reinstall(
                venv_dir=venv_dir,
                package=package,
                local_bin_dir=local_bin_dir,
                python=python,
                verbose=verbose,
            )
        except PipxError as e:
            print(e, file=sys.stderr)
            failed.append(package)
    if len(failed) > 0:
        raise PipxError(
            f"The following package(s) failed to reinstall: {', '.join(failed)}"
        )
