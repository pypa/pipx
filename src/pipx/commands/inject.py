import os
import sys
from pathlib import Path
from typing import List, Optional

from pipx import paths
from pipx.colors import bold
from pipx.commands.common import package_name_from_spec, run_post_install_actions
from pipx.constants import EXIT_CODE_INJECT_ERROR, EXIT_CODE_OK, ExitCode
from pipx.emojis import stars
from pipx.util import PipxError
from pipx.venv import Venv


def inject_dep(
    venv_dir: Path,
    package_name: Optional[str],
    package_spec: str,
    pip_args: List[str],
    *,
    verbose: bool,
    include_apps: bool,
    include_dependencies: bool,
    force: bool,
    suffix: bool = False,
) -> bool:
    if not venv_dir.exists() or not next(venv_dir.iterdir()):
        raise PipxError(
            f"""
            Can't inject {package_spec!r} into nonexistent Virtual Environment
            {venv_dir.name!r}. Be sure to install the package first with 'pipx
            install {venv_dir.name}' before injecting into it.
            """
        )

    venv = Venv(venv_dir, verbose=verbose)
    venv.check_upgrade_shared_libs(pip_args=pip_args, verbose=verbose)

    if not venv.package_metadata:
        raise PipxError(
            f"""
            Can't inject {package_spec!r} into Virtual Environment
            {venv.name!r}. {venv.name!r} has missing internal pipx metadata. It
            was likely installed using a pipx version before 0.15.0.0. Please
            uninstall and install {venv.name!r}, or reinstall-all to fix.
            """
        )

    # package_spec is anything pip-installable, including package_name, vcs spec,
    #   zip file, or tar.gz file.
    if package_name is None:
        package_name = package_name_from_spec(
            package_spec,
            os.fspath(venv.python_path),
            pip_args=pip_args,
            verbose=verbose,
        )
    if suffix:
        venv_suffix = venv.package_metadata[venv.main_package_name].suffix
    else:
        venv_suffix = ""
    venv.install_package(
        package_name=package_name,
        package_or_url=package_spec,
        pip_args=pip_args,
        include_dependencies=include_dependencies,
        include_apps=include_apps,
        is_main_package=False,
        suffix=venv_suffix,
    )
    if include_apps:
        run_post_install_actions(
            venv,
            package_name,
            paths.ctx.bin_dir,
            paths.ctx.man_dir,
            venv_dir,
            include_dependencies,
            force=force,
        )

    print(f"  injected package {bold(package_name)} into venv {bold(venv.name)}")
    print(f"done! {stars}", file=sys.stderr)

    # Any failure to install will raise PipxError, otherwise success
    return True


def inject(
    venv_dir: Path,
    package_name: Optional[str],
    package_specs: List[str],
    pip_args: List[str],
    *,
    verbose: bool,
    include_apps: bool,
    include_dependencies: bool,
    force: bool,
    suffix: bool = False,
) -> ExitCode:
    """Returns pipx exit code."""
    if not include_apps and include_dependencies:
        include_apps = True
    all_success = True
    for dep in package_specs:
        all_success &= inject_dep(
            venv_dir,
            None,
            dep,
            pip_args,
            verbose=verbose,
            include_apps=include_apps,
            include_dependencies=include_dependencies,
            force=force,
            suffix=suffix,
        )

    # Any failure to install will raise PipxError, otherwise success
    return EXIT_CODE_OK if all_success else EXIT_CODE_INJECT_ERROR
