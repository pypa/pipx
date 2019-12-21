"""The implementation of pipx commands"""

import logging
import sys
import textwrap
from pathlib import Path
from shutil import which
from typing import List

try:
    # Instantiating a Pool() attempts to import multiprocessing.synchronize,
    # which fails if the underlying OS does not support semaphores.
    # Here, we import ahead of time to decide which Pool implementation to use:
    # one backed by Processes (the default), or one backed by Threads
    import multiprocessing.synchronize  # noqa: F401
except ImportError:
    # Fallback to Threads on platforms that do not support semaphores
    # https://github.com/pipxproject/pipx/issues/229
    from multiprocessing.dummy import Pool
else:
    from multiprocessing import Pool

import userpath  # type: ignore
from pipx import constants
from pipx.colors import bold
from pipx.commands.common import _get_package_summary, expose_apps_globally
from pipx.emojies import hazard, sleep, stars
from pipx.util import WINDOWS, PipxError, rmdir
from pipx.venv import Venv, VenvContainer, PackageInstallFailureError


def install(
    venv_dir: Path,
    package: str,
    package_or_url: str,
    local_bin_dir: Path,
    python: str,
    pip_args: List[str],
    venv_args: List[str],
    verbose: bool,
    *,
    force: bool,
    include_dependencies: bool,
):
    try:
        exists = venv_dir.exists() and next(venv_dir.iterdir())
    except StopIteration:
        exists = False

    if exists:
        if force:
            print(f"Installing to existing directory {str(venv_dir)!r}")
        else:
            print(
                f"{package!r} already seems to be installed. "
                f"Not modifying existing installation in {str(venv_dir)!r}. "
                "Pass '--force' to force installation."
            )
            return

    venv = Venv(venv_dir, python=python, verbose=verbose)
    try:
        venv.create_venv(venv_args, pip_args)
        try:
            venv.install_package(
                package=package,
                package_or_url=package_or_url,
                pip_args=pip_args,
                include_dependencies=include_dependencies,
                include_apps=True,
                is_main_package=True,
            )
        except PackageInstallFailureError:
            venv.remove_venv()
            raise PipxError(
                f"Could not install package {package}. Is the name or spec correct?"
            )

        _run_post_install_actions(
            venv, package, local_bin_dir, venv_dir, include_dependencies, force=force
        )
    except (Exception, KeyboardInterrupt):
        print("")
        venv.remove_venv()
        raise


def _run_post_install_actions(
    venv: Venv,
    package: str,
    local_bin_dir: Path,
    venv_dir: Path,
    include_dependencies: bool,
    *,
    force: bool,
):
    package_metadata = venv.package_metadata[package]

    if not package_metadata.app_paths and not include_dependencies:
        # No apps associated with this package and we aren't including dependencies.
        # This package has nothing for pipx to use, so this is an error.
        for dep, dependent_apps in package_metadata.app_paths_of_dependencies.items():
            print(
                f"Note: Dependent package '{dep}' contains {len(dependent_apps)} apps"
            )
            for app in dependent_apps:
                print(f"  - {app.name}")

        if venv.safe_to_remove():
            venv.remove_venv()

        if len(package_metadata.app_paths_of_dependencies.keys()):
            raise PipxError(
                f"No apps associated with package {package}. "
                "Try again with '--include-deps' to include apps of dependent packages, "
                "which are listed above. "
                "If you are attempting to install a library, pipx should not be used. "
                "Consider using pip or a similar tool instead."
            )
        else:
            raise PipxError(
                f"No apps associated with package {package}. "
                "If you are attempting to install a library, pipx should not be used. "
                "Consider using pip or a similar tool instead."
            )

    if package_metadata.apps:
        pass
    elif package_metadata.apps_of_dependencies and include_dependencies:
        pass
    else:
        # No apps associated with this package and we aren't including dependencies.
        # This package has nothing for pipx to use, so this is an error.
        if venv.safe_to_remove():
            venv.remove_venv()
        raise PipxError(
            f"No apps associated with package {package} or its dependencies."
            "If you are attempting to install a library, pipx should not be used. "
            "Consider using pip or a similar tool instead."
        )

    expose_apps_globally(
        local_bin_dir, package_metadata.app_paths, package, force=force
    )

    if include_dependencies:
        for _, app_paths in package_metadata.app_paths_of_dependencies.items():
            expose_apps_globally(local_bin_dir, app_paths, package, force=force)

    print(_get_package_summary(venv_dir, package=package, new_install=True))
    _warn_if_not_on_path(local_bin_dir)
    print(f"done! {stars}", file=sys.stderr)


def _warn_if_not_on_path(local_bin_dir: Path):
    if not userpath.in_current_path(str(local_bin_dir)):
        logging.warning(
            f"{hazard}  Note: {str(local_bin_dir)!r} is not on your PATH environment "
            "variable. These apps will not be globally accessible until "
            "your PATH is updated. Run `pipx ensurepath` to "
            "automatically add it, or manually modify your PATH in your shell's "
            "config file (i.e. ~/.bashrc)."
        )


def inject(
    venv_dir: Path,
    package: str,
    package_or_url: str,
    pip_args: List[str],
    *,
    verbose: bool,
    include_apps: bool,
    include_dependencies: bool,
    force: bool,
):
    if not venv_dir.exists() or not next(venv_dir.iterdir()):
        raise PipxError(
            textwrap.dedent(
                f"""\
            Can't inject {package!r} into nonexistent Virtual Environment {str(venv_dir)!r}.
            Be sure to install the package first with pipx install {venv_dir.name!r}
            before injecting into it."""
            )
        )

    venv = Venv(venv_dir, verbose=verbose)
    try:
        venv.install_package(
            package=package,
            package_or_url=package_or_url,
            pip_args=pip_args,
            include_dependencies=include_dependencies,
            include_apps=include_apps,
            is_main_package=False,
        )
    except PackageInstallFailureError:
        raise PipxError(
            f"Could not inject package {package}. Is the name or spec correct?"
        )
    if include_apps:
        _run_post_install_actions(
            venv,
            package,
            constants.LOCAL_BIN_DIR,
            venv_dir,
            include_dependencies,
            force=force,
        )

    print(f"  injected package {bold(package)} into venv {bold(venv_dir.name)}")
    print(f"done! {stars}", file=sys.stderr)


def uninstall(venv_dir: Path, package: str, local_bin_dir: Path, verbose: bool):
    """Uninstall entire venv_dir, including main package and all injected
    packages.
    """
    if not venv_dir.exists():
        print(f"Nothing to uninstall for {package} 😴")
        app = which(package)
        if app:
            print(
                f"{hazard}  Note: '{app}' still exists on your system and is on your PATH"
            )
        return

    venv = Venv(venv_dir, verbose=verbose)

    if venv.pipx_metadata.main_package is not None:
        app_paths: List[Path] = []
        for viewed_package in venv.package_metadata.values():
            app_paths += viewed_package.app_paths
            for dep_paths in viewed_package.app_paths_of_dependencies.values():
                app_paths += dep_paths
    else:
        # fallback if not metadata from pipx_metadata.json
        if venv.python_path.is_file():
            # has a valid python interpreter and can get metadata about the package
            metadata = venv.get_venv_metadata_for_package(package)
            app_paths = metadata.app_paths
            for dep_paths in metadata.app_paths_of_dependencies.values():
                app_paths += dep_paths
        else:
            # Doesn't have a valid python interpreter. We'll take our best guess on what to uninstall
            # here based on symlink location. pipx doesn't use symlinks on windows, so this is for
            # non-windows only.
            # The heuristic here is any symlink in ~/.local/bin pointing to .local/pipx/venvs/PACKAGE/bin
            # should be uninstalled.
            if WINDOWS:
                app_paths = []
            else:
                apps_linking_to_venv_bin_dir = [
                    f
                    for f in constants.LOCAL_BIN_DIR.iterdir()
                    if str(f.resolve()).startswith(str(venv.bin_path))
                ]
                app_paths = apps_linking_to_venv_bin_dir

    for file in local_bin_dir.iterdir():
        if WINDOWS:
            for b in app_paths:
                if file.name == b.name:
                    file.unlink()
        else:
            symlink = file
            for b in app_paths:
                if symlink.exists() and b.exists() and symlink.samefile(b):
                    logging.info(f"removing symlink {str(symlink)}")
                    symlink.unlink()

    rmdir(venv_dir)
    print(f"uninstalled {package}! {stars}")


def uninstall_all(venv_container: VenvContainer, local_bin_dir: Path, verbose: bool):
    for venv_dir in venv_container.iter_venv_dirs():
        package = venv_dir.name
        uninstall(venv_dir, package, local_bin_dir, verbose)


def reinstall_all(
    venv_container: VenvContainer,
    local_bin_dir: Path,
    python: str,
    verbose: bool,
    *,
    skip: List[str],
):
    for venv_dir in venv_container.iter_venv_dirs():
        package = venv_dir.name
        if package in skip:
            continue

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
                raise PipxError("Internal Error injecting package")
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


def list_packages(venv_container: VenvContainer):
    dirs = list(sorted(venv_container.iter_venv_dirs()))
    if not dirs:
        print(f"nothing has been installed with pipx {sleep}")
        return

    print(f"venvs are in {bold(str(venv_container))}")
    print(f"apps are exposed on your $PATH at {bold(str(constants.LOCAL_BIN_DIR))}")

    venv_container.verify_shared_libs()

    with Pool() as p:
        for package_summary in p.map(_get_package_summary, dirs):
            print(package_summary)


def run_pip(package: str, venv_dir: Path, pip_args: List[str], verbose: bool):
    venv = Venv(venv_dir, verbose=verbose)
    if not venv.python_path.exists():
        raise PipxError(
            f"venv for {package!r} was not found. Was {package!r} installed with pipx?"
        )
    venv.verbose = True
    venv._run_pip(pip_args)


def ensurepath(location: Path, *, force: bool):
    location_str = str(location)

    post_install_message = (
        "You likely need to open a new terminal or re-login for "
        "the changes to take effect."
    )
    if userpath.in_current_path(location_str) or userpath.need_shell_restart(
        location_str
    ):
        if not force:
            if userpath.need_shell_restart(location_str):
                print(
                    f"{location_str} has been already been added to PATH. "
                    f"{post_install_message}"
                )
            else:
                logging.warning(
                    (
                        f"The directory `{location_str}` is already in PATH. If you "
                        "are sure you want to proceed, try again with "
                        "the '--force' flag.\n\n"
                        f"Otherwise pipx is ready to go! {stars}"
                    )
                )
            return

    userpath.append(location_str)
    print(f"Success! Added {location_str} to the PATH environment variable.")
    print(
        "Consider adding shell completions for pipx. "
        "Run 'pipx completions' for instructions."
    )
    print()
    print(f"{post_install_message} {stars}")
