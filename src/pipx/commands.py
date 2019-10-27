"""The implementation of pipx commands"""

import datetime
import hashlib
import logging
import multiprocessing
import shlex
import shutil
import subprocess
import sys
import textwrap
import time
import urllib.parse
import urllib.request
from pathlib import Path
from shutil import which
from typing import List

import userpath  # type: ignore

from pipx import constants
from pipx.colors import bold, red
from pipx.constants import PIPX_PACKAGE_NAME, TEMP_VENV_EXPIRATION_THRESHOLD_DAYS
from pipx.emojies import hazard, sleep, stars
from pipx.util import (
    WINDOWS,
    PipxError,
    get_pypackage_bin_path,
    mkdir,
    rmdir,
    run_pypackage_bin,
)
from pipx.venv import Venv, VenvContainer


def run(
    app: str,
    package_or_url: str,
    binary_args: List[str],
    python: str,
    pip_args: List[str],
    venv_args: List[str],
    pypackages: bool,
    verbose: bool,
    use_cache: bool,
):
    """Installs venv to temporary dir (or reuses cache), then runs app from
    package
    """

    if urllib.parse.urlparse(app).scheme:
        if not app.endswith(".py"):
            raise PipxError(
                "pipx will only execute apps from the internet directly if "
                "they end with '.py'. To run from an SVN, try pipx --spec URL BINARY"
            )
        logging.info("Detected url. Downloading and executing as a Python file.")

        content = _http_get_request(app)
        try:
            return subprocess.run([str(python), "-c", content]).returncode
        except KeyboardInterrupt:
            return 1

    elif which(app):
        logging.warning(
            f"{hazard}  {app} is already on your PATH and installed at "
            f"{which(app)}. Downloading and "
            "running anyway."
        )

    if WINDOWS and not app.endswith(".exe"):
        app = f"{app}.exe"
        logging.warning(f"Assuming app is {app!r} (Windows only)")

    pypackage_bin_path = get_pypackage_bin_path(app)
    if pypackage_bin_path.exists():
        logging.info(
            f"Using app in local __pypackages__ directory at {str(pypackage_bin_path)}"
        )
        return run_pypackage_bin(pypackage_bin_path, binary_args)
    if pypackages:
        raise PipxError(
            f"'--pypackages' flag was passed, but {str(pypackage_bin_path)!r} was "
            "not found. See https://github.com/cs01/pythonloc to learn how to "
            "install here, or omit the flag."
        )

    venv_dir = _get_temporary_venv_path(package_or_url, python, pip_args, venv_args)

    venv = Venv(venv_dir)
    bin_path = venv.bin_path / app
    _prepare_venv_cache(venv, bin_path, use_cache)

    if bin_path.exists():
        logging.info(f"Reusing cached venv {venv_dir}")
        retval = venv.run_app(app, binary_args)
    else:
        logging.info(f"venv location is {venv_dir}")
        retval = _download_and_run(
            Path(venv_dir),
            package_or_url,
            app,
            binary_args,
            python,
            pip_args,
            venv_args,
            verbose,
        )

    if not use_cache:
        rmdir(venv_dir)
    return retval


def _download_and_run(
    venv_dir: Path,
    package: str,
    app: str,
    binary_args: List[str],
    python: str,
    pip_args: List[str],
    venv_args: List[str],
    verbose: bool,
):
    venv = Venv(venv_dir, python=python, verbose=verbose)
    venv.create_venv(venv_args, pip_args)
    venv.install_package(package, pip_args)

    if not (venv.bin_path / app).exists():
        apps = venv.get_venv_metadata_for_package(package).apps
        raise PipxError(
            f"'{app}' executable script not found in package '{package}'. "
            "Available executable scripts: "
            f"{', '.join(b for b in apps)}"
        )
    return venv.run_app(app, binary_args)


def _get_temporary_venv_path(
    package_or_url: str, python: str, pip_args: List[str], venv_args: List[str]
):
    """Computes deterministic path using hashing function on arguments relevant
    to virtual environment's end state. Arguments used should result in idempotent
    virtual environment. (i.e. args passed to app aren't relevant, but args
    passed to venv creation are.)
    """
    m = hashlib.sha256()
    m.update(package_or_url.encode())
    m.update(python.encode())
    m.update("".join(pip_args).encode())
    m.update("".join(venv_args).encode())
    venv_folder_name = m.hexdigest()[0:15]  # 15 chosen arbitrarily
    return Path(constants.PIPX_VENV_CACHEDIR) / venv_folder_name


def _is_temporary_venv_expired(venv_dir: Path):
    created_time_sec = venv_dir.stat().st_ctime
    current_time_sec = time.mktime(datetime.datetime.now().timetuple())
    age = current_time_sec - created_time_sec
    expiration_threshold_sec = 60 * 60 * 24 * TEMP_VENV_EXPIRATION_THRESHOLD_DAYS
    return age > expiration_threshold_sec


def _prepare_venv_cache(venv: Venv, bin_path: Path, use_cache: bool):
    venv_dir = venv.root
    if not use_cache and bin_path.exists():
        logging.info(f"Removing cached venv {str(venv_dir)}")
        rmdir(venv_dir)
    _remove_all_expired_venvs()


def _remove_all_expired_venvs():
    for venv_dir in Path(constants.PIPX_VENV_CACHEDIR).iterdir():
        if _is_temporary_venv_expired(venv_dir):
            logging.info(f"Removing expired venv {str(venv_dir)}")
            rmdir(venv_dir)


def _http_get_request(url: str):
    try:
        res = urllib.request.urlopen(url)
        charset = res.headers.get_content_charset() or "utf-8"  # type: ignore
        return res.read().decode(charset)
    except Exception as e:
        raise PipxError(str(e))


def upgrade(
    venv_dir: Path,
    package: str,
    package_or_url: str,
    pip_args: List[str],
    verbose: bool,
    *,
    upgrading_all: bool,
    include_dependencies: bool,
    force: bool,
) -> int:
    """Returns nonzero if package was upgraded, 0 if version did not change"""

    if not venv_dir.is_dir():
        raise PipxError(
            f"Package is not installed. Expected to find {str(venv_dir)}, "
            "but it does not exist."
        )

    venv = Venv(venv_dir, verbose=verbose)

    old_package_metadata = venv.package_metadata[package]
    old_version = old_package_metadata.package_version

    # if default package_or_url, check pipx_metadata for better url
    # TODO 20190926: main.py should communicate if this is spec or copied from
    #   package
    if package_or_url == package:
        if venv.pipx_metadata.main_package.package_or_url is not None:
            package_or_url = venv.pipx_metadata.main_package.package_or_url
        else:
            package_or_url = package

    # Upgrade shared libraries (pip, setuptools and wheel)
    venv.upgrade_packaging_libraries(pip_args)

    venv.upgrade_package(package_or_url, pip_args)
    # TODO 20191026: Should we upgrade injected packages also?

    venv.update_package_metadata(
        package=package,
        package_or_url=package_or_url,
        pip_args=old_package_metadata.pip_args,
        # TODO 20191026: should this be `include_dependencies`?
        include_dependencies=old_package_metadata.include_dependencies,
        include_apps=old_package_metadata.include_apps,
        is_main=True,
    )

    package_metadata = venv.package_metadata[package]
    new_version = package_metadata.package_version

    _expose_apps_globally(
        constants.LOCAL_BIN_DIR, package_metadata.app_paths, package, force=force
    )

    if include_dependencies:
        for _, app_paths in package_metadata.app_paths_of_dependencies.items():
            _expose_apps_globally(
                constants.LOCAL_BIN_DIR, app_paths, package, force=force
            )

    if old_version == new_version:
        if upgrading_all:
            pass
        else:
            print(
                f"{package} is already at latest version {old_version} (location: {str(venv_dir)})"
            )
        return 0
    else:
        print(
            f"upgraded package {package} from {old_version} to {new_version} (location: {str(venv_dir)})"
        )
        return 1


def upgrade_all(
    venv_container: VenvContainer, verbose: bool, *, skip: List[str], force: bool
):
    packages_upgraded = 0
    num_packages = 0
    for venv_dir in venv_container.iter_venv_dirs():
        num_packages += 1
        package = venv_dir.name
        venv = Venv(venv_dir, verbose=verbose)
        if package in skip:
            continue
        if package == "pipx":
            package_or_url = PIPX_PACKAGE_NAME
        else:
            if venv.pipx_metadata.main_package.package_or_url is not None:
                package_or_url = venv.pipx_metadata.main_package.package_or_url
            else:
                package_or_url = package
        try:
            packages_upgraded += upgrade(
                venv_dir,
                package,
                package_or_url,
                venv.pipx_metadata.main_package.pip_args,
                verbose,
                upgrading_all=True,
                include_dependencies=venv.pipx_metadata.main_package.include_dependencies,
                force=force,
            )
        # TODO 20191024: Upgrade injected packages

        except Exception:
            logging.error(f"Error encountered when upgrading {package}")

    if packages_upgraded == 0:
        print(
            f"Versions did not change after running 'pip upgrade' for each package {sleep}"
        )


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
        venv.install_package(package_or_url, pip_args)
        # if installed ok, write pipx_metadata
        venv.update_package_metadata(
            package=package,
            package_or_url=package_or_url,
            pip_args=pip_args,
            include_dependencies=include_dependencies,
            include_apps=True,
            is_main=True,
        )

        if venv.package_metadata[package].package_version is None:
            venv.remove_venv()
            raise PipxError(f"Could not find package {package}. Is the name correct?")

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

    _expose_apps_globally(
        local_bin_dir, package_metadata.app_paths, package, force=force
    )

    if include_dependencies:
        for _, app_paths in package_metadata.app_paths_of_dependencies.items():
            _expose_apps_globally(local_bin_dir, app_paths, package, force=force)

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
    venv.install_package(package_or_url, pip_args)
    # TODO 20191026: verify installed ok like install()?
    venv.update_package_metadata(
        package=package,
        package_or_url=package_or_url,
        pip_args=pip_args,
        include_apps=include_apps,
        include_dependencies=include_dependencies,
        is_main=False,
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

    # TODO 20191024: Uninstall injected packages apps in bin
    # TODO 20191026: Handle error if package is not installed?
    venv = Venv(venv_dir, verbose=verbose)

    if venv.pipx_metadata.main_package is not None:
        all_packages = [venv.pipx_metadata.main_package] + list(
            venv.pipx_metadata.injected_packages.values()
        )
        app_paths: List[Path] = []
        for viewed_package in all_packages:
            app_paths += viewed_package.app_paths
            for dep_paths in viewed_package.app_paths_of_dependencies.values():
                app_paths += dep_paths
    else:
        venv_package_metadata = venv.get_venv_metadata_for_package(package)
        app_paths = venv_package_metadata.app_paths
        for dep_paths in venv_package_metadata.app_paths_of_dependencies.values():
            app_paths += dep_paths

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

        # TODO 20191026: store this away in case uninstalling removes metadata
        # orig_pipx_metadata = venv.pipx_metadata

        uninstall(venv_dir, package, local_bin_dir, verbose)
        # TODO 20191026: also uninstall all injected packages
        #   injected packages will be cluttering up metadata if their metadata
        #   is not removed also

        if venv.pipx_metadata.main_package.package_or_url is not None:
            package_or_url = venv.pipx_metadata.main_package.package_or_url
        else:
            package_or_url = package

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


def _expose_apps_globally(
    local_bin_dir: Path, app_paths: List[Path], package: str, *, force: bool
):
    if WINDOWS:
        _copy_package_apps(local_bin_dir, app_paths, package)
    else:
        _symlink_package_apps(local_bin_dir, app_paths, package, force=force)


def _copy_package_apps(local_bin_dir: Path, app_paths: List[Path], package: str):
    for src_unresolved in app_paths:
        src = src_unresolved.resolve()
        app = src.name
        dest = Path(local_bin_dir / app)
        if not dest.parent.is_dir():
            mkdir(dest.parent)
        if dest.exists():
            logging.warning(f"{hazard}  Overwriting file {str(dest)} with {str(src)}")
            dest.unlink()
        if src.exists():
            shutil.copy(src, dest)


def _symlink_package_apps(
    local_bin_dir: Path, app_paths: List[Path], package: str, *, force: bool
):
    for app_path in app_paths:
        app_name = app_path.name
        symlink_path = Path(local_bin_dir / app_name)
        if not symlink_path.parent.is_dir():
            mkdir(symlink_path.parent)

        if force:
            logging.info(f"Force is true. Removing {str(symlink_path)}.")
            try:
                symlink_path.unlink()
            except FileNotFoundError:
                pass
            except IsADirectoryError:
                rmdir(symlink_path)

        exists = symlink_path.exists()
        is_symlink = symlink_path.is_symlink()
        if exists:
            if symlink_path.samefile(app_path):
                logging.info(f"Same path {str(symlink_path)} and {str(app_path)}")
            else:
                logging.warning(
                    f"{hazard}  File exists at {str(symlink_path)} and points "
                    f"to {symlink_path.resolve()}, not {str(app_path)}. Not modifying."
                )
            continue
        if is_symlink and not exists:
            logging.info(
                f"Removing existing symlink {str(symlink_path)} since it "
                "pointed non-existent location"
            )
            symlink_path.unlink()

        existing_executable_on_path = which(app_name)
        symlink_path.symlink_to(app_path)

        if existing_executable_on_path:
            logging.warning(
                f"{hazard}  Note: {app_name} was already on your PATH at "
                f"{existing_executable_on_path}"
            )


def _get_package_summary(
    path: Path, *, package: str = None, new_install: bool = False
) -> str:
    venv = Venv(path)
    python_path = venv.python_path.resolve()
    if package is None:
        package = path.name
    package_metadata = venv.package_metadata[package]

    if package_metadata.package_version is None:
        not_installed = red("is not installed")
        return f"   package {bold(package)} {not_installed} in the venv {str(path)}"

    apps = package_metadata.apps + package_metadata.apps_of_dependencies
    exposed_app_paths = _get_exposed_app_paths_for_package(
        venv.bin_path, apps, constants.LOCAL_BIN_DIR
    )
    exposed_binary_names = sorted(p.name for p in exposed_app_paths)
    unavailable_binary_names = sorted(
        set(package_metadata.apps) - set(exposed_binary_names)
    )
    # The following is to satisfy mypy that python_version is str and not
    #   Optional[str]
    python_version = (
        venv.pipx_metadata.python_version
        if venv.pipx_metadata.python_version is not None
        else ""
    )
    return _get_list_output(
        python_version,
        python_path,
        package_metadata.package_version,
        package,
        new_install,
        exposed_binary_names,
        unavailable_binary_names,
    )


def _get_list_output(
    python_version: str,
    python_path: Path,
    package_version: str,
    package: str,
    new_install: bool,
    exposed_binary_names: List[str],
    unavailable_binary_names: List[str],
) -> str:
    output = []
    output.append(
        f"  {'installed' if new_install else ''} package {bold(shlex.quote(package))} {bold(package_version)}, {python_version}"
    )

    if not python_path.exists():
        output.append(f"    associated python path {str(python_path)} does not exist!")

    if new_install and exposed_binary_names:
        output.append("  These apps are now globally available")
    for name in exposed_binary_names:
        output.append(f"    - {name}")
    for name in unavailable_binary_names:
        output.append(
            f"    - {red(name)} (symlink missing or pointing to unexpected location)"
        )
    return "\n".join(output)


def list_packages(venv_container: VenvContainer):
    dirs = list(sorted(venv_container.iter_venv_dirs()))
    if not dirs:
        print(f"nothing has been installed with pipx {sleep}")
        return

    print(f"venvs are in {bold(str(venv_container))}")
    print(f"apps are exposed on your $PATH at {bold(str(constants.LOCAL_BIN_DIR))}")

    venv_container.verify_shared_libs()

    with multiprocessing.Pool() as p:
        for package_summary in p.map(_get_package_summary, dirs):
            print(package_summary)


def _get_exposed_app_paths_for_package(
    venv_bin_path: Path, package_binary_names: List[str], local_bin_dir: Path
):
    bin_symlinks = set()
    for b in local_bin_dir.iterdir():
        try:
            # sometimes symlinks can resolve to a file of a different name
            # (in the case of ansible for example) so checking the resolved paths
            # is not a reliable way to determine if the symlink exists.
            # windows doesn't use symlinks, so the check is less strict.
            if WINDOWS and b.name in package_binary_names:
                is_same_file = True
            else:
                is_same_file = b.resolve().parent.samefile(venv_bin_path)
            if is_same_file:
                bin_symlinks.add(b)

        except FileNotFoundError:
            pass
    return bin_symlinks


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
