#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import hashlib
import logging
import multiprocessing
import os
import shlex
import shutil
import subprocess
import textwrap
import time
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from shutil import which
from typing import List, Optional

from .animate import animate
from .colors import bold, red
from .constants import (
    LOCAL_BIN_DIR,
    PIPX_PACKAGE_NAME,
    PIPX_VENV_CACHEDIR,
    TEMP_VENV_EXPIRATION_THRESHOLD_DAYS,
)
from .emojies import hazard, sleep, stars
from .util import (
    WINDOWS,
    PipxError,
    get_pypackage_bin_path,
    mkdir,
    rmdir,
    run_pypackage_bin,
)
from .Venv import Venv


def run(
    binary: str,
    package_or_url: str,
    binary_args: List[str],
    python: str,
    pip_args: List[str],
    venv_args: List[str],
    pypackages: bool,
    verbose: bool,
    use_cache: bool,
):
    """Installs venv to temporary dir (or reuses cache), then runs binary from
    package
    """

    if urllib.parse.urlparse(binary).scheme:
        if not binary.endswith(".py"):
            exit(
                "pipx will only execute binaries from the internet directly if "
                "they end with '.py'. To run from an SVN, try pipx --spec URL BINARY"
            )
        logging.info("Detected url. Downloading and executing as a Python file.")

        content = _http_get_request(binary)
        try:
            exit(subprocess.run([str(python), "-c", content]).returncode)
        except KeyboardInterrupt:
            pass
        exit(0)
    elif which(binary):
        logging.warning(
            f"{hazard}  {binary} is already on your PATH and installed at "
            f"{which(binary)}. Downloading and "
            "running anyway."
        )

    if WINDOWS and not binary.endswith(".exe"):
        binary = f"{binary}.exe"
        logging.warning(f"Assuming binary is {binary!r} (Windows only)")

    pypackage_bin_path = get_pypackage_bin_path(binary)
    if pypackage_bin_path.exists():
        logging.info(
            f"Using binary in local __pypackages__ directory at {str(pypackage_bin_path)}"
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
    bin_path = venv.bin_path / binary
    _prepare_venv_cache(venv, bin_path, use_cache)

    if bin_path.exists():
        logging.info(f"Reusing cached venv {venv_dir}")
        retval = venv.run_binary(binary, binary_args)
    else:
        logging.info(f"venv location is {venv_dir}")
        retval = _download_and_run(
            Path(venv_dir),
            package_or_url,
            binary,
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
    binary: str,
    binary_args: List[str],
    python: str,
    pip_args: List[str],
    venv_args: List[str],
    verbose: bool,
):
    venv = Venv(venv_dir, python=python, verbose=verbose)
    venv.create_venv(venv_args, pip_args)
    venv.install_package(package, pip_args)
    if not (venv.bin_path / binary).exists():
        binaries = venv.get_venv_metadata_for_package(package).binaries
        raise PipxError(
            f"{binary} not found in package {package}. Available binaries: "
            f"{', '.join(b for b in binaries)}"
        )
    return venv.run_binary(binary, binary_args)


def _get_temporary_venv_path(
    package_or_url: str, python: str, pip_args: List[str], venv_args: List[str]
):
    """Computes deterministic path using hashing function on arguments relevant
    to virtual environment's end state. Arguments used should result in idempotent
    virtual environment. (i.e. args passed to binary aren't relevant, but args
    passed to venv creation are.)
    """
    m = hashlib.sha256()
    m.update(package_or_url.encode())
    m.update(python.encode())
    m.update("".join(pip_args).encode())
    m.update("".join(venv_args).encode())
    venv_folder_name = m.hexdigest()[0:15]  # 15 chosen arbitrarily
    return Path(PIPX_VENV_CACHEDIR) / venv_folder_name


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
    for venv_dir in Path(PIPX_VENV_CACHEDIR).iterdir():
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
    include_deps: bool,
) -> int:
    """Returns nonzero if package was upgraded, 0 if version did not change"""

    if not venv_dir.is_dir():
        raise PipxError(
            f"Package is not installed. Expected to find {str(venv_dir)}, "
            "but it does not exist."
        )

    venv = Venv(venv_dir, verbose=verbose)

    old_version = venv.get_venv_metadata_for_package(package).package_version
    do_animation = not verbose
    try:
        with animate(f"upgrading pip for package {package_or_url!r}", do_animation):
            venv.upgrade_package("pip", pip_args)

    except Exception:
        logging.error("Failed to upgrade pip", exc_info=True)

    with animate(f"upgrading package {package_or_url!r}", do_animation):
        venv.upgrade_package(package_or_url, pip_args)
    new_version = venv.get_venv_metadata_for_package(package).package_version

    metadata = venv.get_venv_metadata_for_package(package)
    _expose_binaries_globally(LOCAL_BIN_DIR, metadata.binary_paths, package)

    if include_deps:
        for _, binary_paths in metadata.binary_paths_of_dependencies.items():
            _expose_binaries_globally(LOCAL_BIN_DIR, binary_paths, package)

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
    pipx_local_venvs: Path,
    pip_args: List[str],
    verbose: bool,
    *,
    include_deps: bool,
    skip: List[str],
):
    packages_upgraded = 0
    num_packages = 0
    for venv_dir in pipx_local_venvs.iterdir():
        num_packages += 1
        package = venv_dir.name
        if package in skip:
            continue
        if package == "pipx":
            package_or_url = PIPX_PACKAGE_NAME
        else:
            package_or_url = package
        try:
            packages_upgraded += upgrade(
                venv_dir,
                package,
                package_or_url,
                pip_args,
                verbose,
                upgrading_all=True,
                include_deps=include_deps,
            )
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
    include_deps: bool,
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
                "Pass '--force' to force installation"
            )
            return

    venv = Venv(venv_dir, python=python, verbose=verbose)
    venv.create_venv(venv_args, pip_args)
    try:
        venv.install_package(package_or_url, pip_args)
    except PipxError:
        venv.remove_venv()
        raise

    if venv.get_venv_metadata_for_package(package).package_version is None:
        venv.remove_venv()
        raise PipxError(f"Could not find package {package}. Is the name correct?")

    _run_post_install_actions(venv, package, local_bin_dir, venv_dir, include_deps)


def _run_post_install_actions(
    venv: Venv, package: str, local_bin_dir: Path, venv_dir: Path, include_deps: bool
):
    metadata = venv.get_venv_metadata_for_package(package)
    if not metadata.binary_paths and not include_deps:
        # No binaries associated with this package and we aren't including dependencies.
        # This package has nothing for pipx to use, so this is an error.
        for dep, dependent_binaries in metadata.binary_paths_of_dependencies.items():
            print(
                f"Note: Dependent package '{dep}' contains {len(dependent_binaries)} binaries"
            )
            for binary in dependent_binaries:
                print(f"  - {binary.name}")

        if venv.safe_to_remove():
            venv.remove_venv()

        if len(metadata.binary_paths_of_dependencies.keys()):
            raise PipxError(
                f"No binaries associated with package {package}. "
                "Try again with '--include-deps' to include binaries of dependent packages."
            )
        else:
            raise PipxError(f"No binaries associated with package {package}. ")

    _expose_binaries_globally(local_bin_dir, metadata.binary_paths, package)

    if include_deps:
        for _, binary_paths in metadata.binary_paths_of_dependencies.items():
            _expose_binaries_globally(local_bin_dir, binary_paths, package)

    print(_get_package_summary(venv_dir, package=package, new_install=True))

    random_binary_name: str
    if metadata.binaries:
        random_binary_name = metadata.binaries[0]
    else:
        random_binary_name = metadata.binaries_of_dependencies[0]

    _warn_if_not_on_path(local_bin_dir, random_binary_name)
    print(f"done! {stars}")


def _warn_if_not_on_path(local_bin_dir: Path, binary: str):
    if not which(binary):
        logging.warning(
            f"{hazard}  Note: {str(local_bin_dir)!r} is not on your PATH environment "
            "variable. These binaries will not be globally accessible until "
            "your PATH is updated. Run `userpath append ~/.local/bin` to "
            "automatically add it, or manually modify your PATH in your shell's "
            "config file (i.e. ~/.bashrc)."
        )


def inject(
    venv_dir: Path,
    package: str,
    pip_args: List[str],
    *,
    verbose: bool,
    include_binaries: bool,
    include_deps: bool,
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
    venv.install_package(package, pip_args)

    if venv.get_venv_metadata_for_package(package).package_version is None:
        raise PipxError(f"Could not find package {package}. Is the name correct?")

    if include_binaries:
        _run_post_install_actions(venv, package, LOCAL_BIN_DIR, venv_dir, include_deps)

    print(f"done! {stars}")


def uninstall(venv_dir: Path, package: str, local_bin_dir: Path, verbose: bool):
    if not venv_dir.exists():
        print(f"Nothing to uninstall for {package} 😴")
        binary = which(package)
        if binary:
            print(
                f"{hazard}  Note: '{binary}' still exists on your system and is on your PATH"
            )
        return

    venv = Venv(venv_dir, verbose=verbose)

    metadata = venv.get_venv_metadata_for_package(package)
    binary_paths = metadata.binary_paths
    for dep_paths in metadata.binary_paths_of_dependencies.values():
        binary_paths += dep_paths
    for file in local_bin_dir.iterdir():
        if WINDOWS:
            for b in binary_paths:
                if file.name == b.name:
                    file.unlink()
        else:
            symlink = file
            for b in binary_paths:
                if symlink.exists() and b.exists() and symlink.samefile(b):
                    logging.info(f"removing symlink {str(symlink)}")
                    symlink.unlink()

    rmdir(venv_dir)
    print(f"uninstalled {package}! {stars}")


def uninstall_all(pipx_local_venvs: Path, local_bin_dir: Path, verbose: bool):
    for venv_dir in pipx_local_venvs.iterdir():
        package = venv_dir.name
        uninstall(venv_dir, package, local_bin_dir, verbose)


def reinstall_all(
    pipx_local_venvs: Path,
    local_bin_dir: Path,
    python: str,
    pip_args: List[str],
    venv_args: List[str],
    verbose: bool,
    include_deps: bool,
    *,
    skip: List[str],
):
    for venv_dir in pipx_local_venvs.iterdir():
        package = venv_dir.name
        if package in skip:
            continue
        uninstall(venv_dir, package, local_bin_dir, verbose)

        package_or_url = package
        install(
            venv_dir,
            package,
            package_or_url,
            local_bin_dir,
            python,
            pip_args,
            venv_args,
            verbose,
            force=True,
            include_deps=include_deps,
        )


def _expose_binaries_globally(
    local_bin_dir: Path, binary_paths: List[Path], package: str
):
    if WINDOWS:
        _copy_package_binaries(local_bin_dir, binary_paths, package)
    else:
        _symlink_package_binaries(local_bin_dir, binary_paths, package)


def _copy_package_binaries(local_bin_dir: Path, binary_paths: List[Path], package: str):
    for src_unresolved in binary_paths:
        src = src_unresolved.resolve()
        binary = src.name
        dest = Path(local_bin_dir / binary)
        if not dest.parent.is_dir():
            mkdir(dest.parent)
        if dest.exists():
            logging.warning(f"{hazard}  Overwriting file {str(dest)} with {str(src)}")
            dest.unlink()
        if src.exists():
            shutil.copy(src, dest)


def _symlink_package_binaries(
    local_bin_dir: Path, binary_paths: List[Path], package: str
):
    for b in binary_paths:
        binary = b.name
        symlink_path = Path(local_bin_dir / binary)
        if not symlink_path.parent.is_dir():
            mkdir(symlink_path.parent)

        if symlink_path.exists():
            if symlink_path.samefile(b):
                pass
            else:
                logging.warning(
                    f"{hazard}  File exists at {str(symlink_path)} and points "
                    f"to {symlink_path.resolve()}. Not modifying."
                )
        else:
            shadow = which(binary)
            try:
                symlink_path.symlink_to(b)
            except FileExistsError:
                pass

            if shadow:
                logging.warning(
                    f"{hazard}  Note: {binary} was already on your PATH at " f"{shadow}"
                )


def _get_package_summary(
    path: Path, *, package: str = None, new_install: bool = False
) -> str:
    venv = Venv(path)
    python_path = venv.python_path.resolve()
    if package is None:
        package = path.name
    metadata = venv.get_venv_metadata_for_package(package)

    if metadata.package_version is None:
        not_installed = red("is not installed")
        return f"   package {bold(package)} {not_installed} in the venv {str(path)}"

    binaries = metadata.binaries + metadata.binaries_of_dependencies
    exposed_binary_paths = _get_exposed_binary_paths_for_package(
        venv.bin_path, binaries, LOCAL_BIN_DIR
    )
    exposed_binary_names = sorted(p.name for p in exposed_binary_paths)
    unavailable_binary_names = sorted(
        set(metadata.binaries) - set(exposed_binary_names)
    )
    return _get_list_output(
        metadata.python_version,
        python_path,
        metadata.package_version,
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
        output.append("  These binaries are now globally available")
    for name in exposed_binary_names:
        output.append(f"    - {name}")
    for name in unavailable_binary_names:
        output.append(f"    - {red(name)} (symlink not installed)")
    return "\n".join(output)


def list_packages(pipx_local_venvs: Path):
    dirs = list(sorted(pipx_local_venvs.iterdir()))
    if not dirs:
        print(f"nothing has been installed with pipx {sleep}")
        return

    print(f"venvs are in {bold(str(pipx_local_venvs))}")
    print(f"binaries are exposed on your $PATH at {bold(str(LOCAL_BIN_DIR))}")

    with multiprocessing.Pool() as p:
        for package_summary in p.map(_get_package_summary, dirs):
            print(package_summary)


def _get_exposed_binary_paths_for_package(
    bin_path: Path, package_binary_names: List[str], local_bin_dir: Path
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
                is_same_file = b.resolve().parent.samefile(bin_path)

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


def ensurepath(bin_dir: Path):
    print("ensurepath command is deprecated. Use 'userpath' instead.", file=sys.stderr)
    print("See https://github.com/pipxproject/pipx for usage.", file=sys.stderr)

    shell = os.environ.get("SHELL", "")
    config_file: Optional[str]
    if "bash" in shell:
        config_file = "~/.bashrc"
    elif "zsh" in shell:
        config_file = "~/.zshrc"
    elif "fish" in shell:
        config_file = "~/.config/fish/config.fish"
    else:
        config_file = None

    if config_file:
        config_file = os.path.expanduser(config_file)

    if config_file and os.path.exists(config_file):
        with open(config_file, "a") as f:
            f.write("\n# added by pipx (https://github.com/pipxproject/pipx)\n")
            if "fish" in shell:
                f.write(f"set -x PATH {str(bin_dir)} $PATH\n\n")
            else:
                f.write(f'export PATH="{str(bin_dir)}{os.pathsep}$PATH"\n')
        print(f"Added {str(bin_dir)} to the PATH environment variable in {config_file}")
        print("")
        print(f"Open a new terminal to use pipx {stars}")
    else:
        if WINDOWS:
            print(
                textwrap.dedent(
                    f"""
                Note {hazard}:
                To finish installation, {str(bin_dir)!r} must be added to your PATH
                environment variable.

                To do this, go to settings and type "Environment Variables".
                In the Environment Variables window edit the PATH variable
                by adding the following to the end of the value, then open a new
                terminal.

                    ;{str(bin_dir)}
            """
                )
            )

        else:
            print(
                textwrap.dedent(
                    f"""
                    Note:
                    To finish installation, {str(bin_dir)!r} must be added to your PATH
                    environemnt variable.

                    To do this, add the following line to your shell
                    config file (such as ~/.bashrc if using bash):

                        export PATH={str(bin_dir)}:$PATH
                """
                )
            )
