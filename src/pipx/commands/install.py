from pathlib import Path
from typing import List, Optional

from pipx import paths
from pipx.commands.common import package_name_from_spec, run_post_install_actions
from pipx.constants import (
    EXIT_CODE_INSTALL_VENV_EXISTS,
    EXIT_CODE_OK,
    ExitCode,
)
from pipx.interpreter import DEFAULT_PYTHON
from pipx.util import pipx_wrap
from pipx.venv import Venv, VenvContainer


def install(
    venv_dir: Optional[Path],
    package_names: Optional[List[str]],
    package_specs: List[str],
    local_bin_dir: Path,
    local_man_dir: Path,
    python: Optional[str],
    pip_args: List[str],
    venv_args: List[str],
    verbose: bool,
    *,
    force: bool,
    reinstall: bool,
    include_dependencies: bool,
    preinstall_packages: Optional[List[str]],
    suffix: str = "",
) -> ExitCode:
    """Returns pipx exit code."""
    # package_spec is anything pip-installable, including package_name, vcs spec,
    #   zip file, or tar.gz file.
    python_flag_was_passed = python is not None

    python = python or DEFAULT_PYTHON

    package_names = package_names or []
    if len(package_names) != len(package_specs):
        package_names = [
            package_name_from_spec(package_spec, python, pip_args=pip_args, verbose=verbose)
            for package_spec in package_specs
        ]

    for package_name, package_spec in zip(package_names, package_specs):
        if venv_dir is None:
            venv_container = VenvContainer(paths.ctx.venvs)
            venv_dir = venv_container.get_venv_dir(f"{package_name}{suffix}")

        try:
            exists = venv_dir.exists() and bool(next(venv_dir.iterdir()))
        except StopIteration:
            exists = False

        venv = Venv(venv_dir, python=python, verbose=verbose)
        venv.check_upgrade_shared_libs(pip_args=pip_args, verbose=verbose)
        if exists:
            if not reinstall and force and python_flag_was_passed:
                print(
                    pipx_wrap(
                        f"""
                        --python is ignored when --force is passed.
                        If you want to reinstall {package_name} with {python},
                        run `pipx reinstall {package_spec} --python {python}` instead.
                        """
                    )
                )
            if force:
                print(f"Installing to existing venv {venv.name!r}")
                pip_args = ["--force-reinstall"] + pip_args
            else:
                print(
                    pipx_wrap(
                        f"""
                        {venv.name!r} already seems to be installed. Not modifying
                        existing installation in '{venv_dir}'. Pass '--force'
                        to force installation.
                        """
                    )
                )
                return EXIT_CODE_INSTALL_VENV_EXISTS

        try:
            # Enable installing shared library `pip` with `pipx`
            override_shared = package_name == "pip"
            venv.create_venv(venv_args, pip_args, override_shared)
            for dep in preinstall_packages or []:
                dep_name = package_name_from_spec(dep, python, pip_args=pip_args, verbose=verbose)
                venv.upgrade_package_no_metadata(dep_name, [])
            venv.install_package(
                package_name=package_name,
                package_or_url=package_spec,
                pip_args=pip_args,
                include_dependencies=include_dependencies,
                include_apps=True,
                is_main_package=True,
                suffix=suffix,
            )
            run_post_install_actions(
                venv,
                package_name,
                local_bin_dir,
                local_man_dir,
                venv_dir,
                include_dependencies,
                force=force,
            )
        except (Exception, KeyboardInterrupt):
            print()
            venv.remove_venv()
            raise

        # Reset venv_dir to None ready to install the next package in the list
        venv_dir = None

    # Any failure to install will raise PipxError, otherwise success
    return EXIT_CODE_OK
