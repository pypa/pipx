import sys
from pathlib import Path
from typing import List, Sequence

from packaging.utils import canonicalize_name

from pipx.commands.inject import inject
from pipx.commands.install import install
from pipx.commands.uninstall import uninstall
from pipx.emojies import sleep
from pipx.util import PipxError
from pipx.venv import Venv, VenvContainer


def reinstall(
    *, venv_dir: Path, local_bin_dir: Path, python: str, verbose: bool,
) -> int:
    """Returns pipx shell exit code"""
    if not venv_dir.exists():
        print(f"Nothing to reinstall for {venv_dir.name} {sleep}")
        return 1

    venv = Venv(venv_dir, verbose=verbose)

    if venv.pipx_metadata.main_package.package_or_url is not None:
        package_or_url = venv.pipx_metadata.main_package.package_or_url
    else:
        package_or_url = venv.main_package_name

    uninstall(venv_dir, local_bin_dir, verbose)

    # install main package first
    install(
        venv_dir,
        venv.main_package_name,
        package_or_url,
        canonicalize_name(local_bin_dir),  # in case legacy original dir name
        python,
        venv.pipx_metadata.main_package.pip_args,
        venv.pipx_metadata.venv_args,
        verbose,
        force=True,
        include_dependencies=venv.pipx_metadata.main_package.include_dependencies,
        suffix=venv.pipx_metadata.main_package.suffix,
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
                f"Internal Error injecting package {injected_package} into {venv.name}"
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

    return 0


def reinstall_all(
    venv_container: VenvContainer,
    local_bin_dir: Path,
    python: str,
    verbose: bool,
    *,
    skip: Sequence[str],
) -> int:
    """Returns pipx shell exit code"""
    failed: List[str] = []
    for venv_dir in venv_container.iter_venv_dirs():
        if venv_dir.name in skip:
            continue
        try:
            reinstall(
                venv_dir=venv_dir,
                local_bin_dir=local_bin_dir,
                python=python,
                verbose=verbose,
            )
        except PipxError as e:
            print(e, file=sys.stderr)
            failed.append(venv_dir.name)
    if len(failed) > 0:
        raise PipxError(
            f"The following package(s) failed to reinstall: {', '.join(failed)}"
        )
    return 0
