from pathlib import Path
from typing import List, Optional

from pipx import constants
from pipx.commands.common import package_name_from_spec, run_post_install_actions
from pipx.constants import EXIT_CODE_INSTALL_VENV_EXISTS, EXIT_CODE_OK, ExitCode
from pipx.util import pipx_wrap
from pipx.venv import Venv, VenvContainer


def install(
    venv_dir: Optional[Path],
    package_name: Optional[str],
    package_spec: str,
    local_bin_dir: Path,
    python: str,
    pip_args: List[str],
    venv_args: List[str],
    verbose: bool,
    *,
    force: bool,
    include_dependencies: bool,
    suffix: str = "",
) -> ExitCode:
    """Returns pipx exit code."""
    # package_spec is anything pip-installable, including package_name, vcs spec,
    #   zip file, or tar.gz file.

    if package_name is None:
        package_name = package_name_from_spec(
            package_spec, python, pip_args=pip_args, verbose=verbose
        )
    if venv_dir is None:
        venv_container = VenvContainer(constants.PIPX_LOCAL_VENVS)
        venv_dir = venv_container.get_venv_dir(f"{package_name}{suffix}")

    try:
        exists = venv_dir.exists() and bool(next(venv_dir.iterdir()))
    except StopIteration:
        exists = False

    venv = Venv(venv_dir, python=python, verbose=verbose)
    if exists:
        if force:
            print(f"Installing to existing venv {venv.name!r}")
        else:
            print(
                pipx_wrap(
                    f"""
                    {venv.name!r} already seems to be installed. Not modifying
                    existing installation in {str(venv_dir)!r}. Pass '--force'
                    to force installation.
                    """
                )
            )
            return EXIT_CODE_INSTALL_VENV_EXISTS

    try:
        venv.create_venv(venv_args, pip_args)
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
            venv_dir,
            include_dependencies,
            force=force,
        )
    except (Exception, KeyboardInterrupt):
        print()
        venv.remove_venv()
        raise

    # Any failure to install will raise PipxError, otherwise success
    return EXIT_CODE_OK
