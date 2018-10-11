#!/usr/bin/env python

"""
Easily run Python CLI programs in a temporary environment with no commitment.

Optionally install using best practices, using virtualenv as non-root user.

Pass a binary to run or a pipx command to run.

binary: The name of the Python CLI program to run such as pip or black. All
arguments before the binary are passed to pipx, all arguments after are passed
directly to the binary when it is invoked.

pipx commands

install: Install a package to your system so its binariess can be run without
re-downloading each time. The installation is done using best practice of
isolating it in a virtualenv as a non-root user. The default installation location
is {DEFAULT_PIPX_HOME} and can be changed by setting the environment variable
PIPX_HOME. Binaries are symlinked in {DEFAULT_PIPX_BIN_DIR}, which can be changed
by setting the environment variable PIPX_BIN_DIR.

uninstall: Uninstalls a package and any symlinks that was installed with pipx.

uninstall-all: Uninstalls all packages, including pipx

list: List installed packages

upgrade: Upgrade a package installed by pipx

upgrade-all: Upgrade all packages installed by pipx
"""


import argparse
import hashlib
import logging
import os
import pkg_resources
import pkgutil
from pathlib import Path
import requests
import shutil
from shutil import which
import subprocess
import sys
import tempfile
import textwrap
import urllib


DEFAULT_PIPX_HOME = Path.home() / ".local/pipx/venvs"
DEFAULT_PIPX_BIN_DIR = Path.home() / ".local/bin"
pipx_local_venvs = os.environ.get("PIPX_HOME", DEFAULT_PIPX_HOME)
local_bin_dir = os.environ.get("PIPX_BIN_DIR", DEFAULT_PIPX_BIN_DIR)
INSTALL_PIPX_URL = "git+https://github.com/cs01/pipx.git"


class PipxError(Exception):
    pass


class Venv:
    def __init__(self, path, *, verbose=False, python="python3"):
        self.root = path
        self._python = python
        self.bin_path = path / "bin"
        self.pip_path = self.bin_path / "pip"
        self.python_path = self.bin_path / "python"
        self.verbose = verbose

    def create_venv(self):
        _run([self._python, "-m", "venv", self.root])
        if not self.pip_path.exists():
            raise PipxError(f"Expected to find pip at {str(self.pip_path)}")
        self.upgrade_package("pip")

    def remove_venv(self):
        rmdir(self.root)

    def install_package(self, package_or_url):
        self._run_pip(["install", package_or_url])

    def get_package_version(self, package):
        # package_venv_path = self.root / package
        get_version_script = textwrap.dedent(
            f"""
        try:
            import pkg_resources
            print(pkg_resources.get_distribution("{package}").version)
        except:
            pass
        """
        )
        version = (
            subprocess.run(
                [self.python_path, "-c", get_version_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            .stdout.decode()
            .strip()
        )
        if version:
            return version
        else:
            return None

    def get_package_binary_paths(self, package):
        get_binaries_script = textwrap.dedent(
            f"""
        import pkg_resources
        import sys

        dist = pkg_resources.get_distribution("{package}")
        binaries = set()
        for _, d in pkg_resources.get_entry_map(dist).items():
            for binary in d:
                binaries.add(binary)
        [print(b) for b in binaries]
        """
        )
        binaries = (
            subprocess.run(
                [self.python_path, "-c", get_binaries_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            .stdout.decode()
            .split()
        )
        binary_paths = [Path(self.bin_path) / b for b in binaries]
        valid_binary_paths = list(filter(lambda p: p.exists(), binary_paths))
        return valid_binary_paths

    def run_binary(self, binary, binary_args):
        cmd = [self.bin_path / binary] + binary_args
        try:
            return _run(cmd, check=False)
        except KeyboardInterrupt:
            pass

    def upgrade_package(self, package_or_url):
        self._run_pip(["install", "--upgrade", package_or_url])

    def _run_pip(self, cmd):
        cmd = [self.pip_path] + cmd
        if not self.verbose:
            cmd.append("-q")
        return _run(cmd)


def _run(cmd, check=True):
    cmd_str = " ".join(str(c) for c in cmd)
    logging.info(f"running {cmd_str}")
    returncode = subprocess.run(cmd).returncode
    if check and returncode:
        raise PipxError(f"{cmd_str!r} failed")
    return returncode


def rmdir(path):
    logging.info(f"removing directory {path}")
    shutil.rmtree(path)


def mkdir(path):
    if path.is_dir():
        return
    logging.info(f"creating directory {path}")
    path.mkdir(parents=True, exist_ok=True)


def download_and_run(venv_dir, package, binary, binary_args, python, verbose):
    venv = Venv(venv_dir, python=python, verbose=verbose)
    venv.create_venv()
    venv.install_package(package)
    if not (venv.bin_path / binary).exists():
        binaries = venv.get_package_binary_paths(package)
        raise PipxError(
            f"{binary} not found in package {package}. Available binaries: "
            f"{', '.join(b.name for b in binaries)}"
        )
    return venv.run_binary(binary, binary_args)


def symlink_package_binaries(local_bin_dir, binary_paths, package):
    for b in binary_paths:
        binary = b.name
        symlink_path = Path(local_bin_dir / binary)
        if not symlink_path.parent.is_dir():
            mkdir(symlink_path.parent)

        if which(binary):
            logging.warning(
                f"{binary} is already on your PATH at "
                f"{Path(which(binary)).resolve()}. Not creating new symlink at {str(symlink_path)}"
            )
        elif symlink_path.exists():
            logging.warning(
                f"File exists at {str(symlink_path)} and points to {symlink_path.resolve()}. Not creating."
            )
        else:
            symlink_path.symlink_to(b)
            print(f"{b.name} from package {package} is now available globally")


def list_packages(pipx_local_venvs):
    dirs = list(sorted(pipx_local_venvs.iterdir()))
    if not dirs:
        print("nothing has been installed with pipx 😴")
        return

    print(
        f"venvs are in {str(pipx_local_venvs)}, binaries symlinks are in {str(local_bin_dir)}"
    )
    for d in dirs:
        venv = Venv(d)
        python_path = venv.python_path.resolve()
        package = d.name
        version = venv.get_package_version(package)
        symlinked_binaries = get_valid_bin_symlinks_for_package(
            venv.bin_path, local_bin_dir
        )
        if version is None:
            print(
                f"pipx installed a package from url to dir {package}. "
                f"Binaries available: {', '.join(symlinked_binaries)}"
            )
            continue
        package_binary_paths = venv.get_package_binary_paths(package)

        package_binary_names = [b.name for b in package_binary_paths]
        unavailable_binary_names = set(package_binary_names) - set(symlinked_binaries)
        unavailable = ""
        if unavailable_binary_names:
            unavailable = (
                f", binaries not symlinked: {', '.join(unavailable_binary_names)}"
            )
        print(
            f"package {package} {version}, binaries symlinks available: {', '.join(symlinked_binaries)}{unavailable}"
        )
        logging.info(f"virtualenv: {str(d)}, python executable: {python_path}")


def get_valid_bin_symlinks_for_package(venv_bin_dir, local_bin_dir):
    symlinks = []
    for b in local_bin_dir.iterdir():
        if (venv_bin_dir / b.name).exists():
            symlinks.append(b.name)
    return symlinks


def upgrade(venv_dir, package, url, verbose):
    if not venv_dir.is_dir():
        raise PipxError(
            f"Package is not installed. Expected to find {str(venv_dir)}, "
            "but it does not exist. If installed with explicit path, try "
            f"`pipx upgrade {package} --url URL`"
        )
    venv = Venv(venv_dir, verbose=verbose)
    venv.upgrade_package(url)
    print(f"upgraded package {package} to latest version (location: {str(venv_dir)})")


def upgrade_all(pipx_local_venvs, verbose):
    for venv_dir in pipx_local_venvs.iterdir():
        package = venv_dir.name
        url = package
        upgrade(venv_dir, package, url, verbose)


def install(venv_dir, package, package_or_url, local_bin_dir, python, verbose):
    if venv_dir.exists():
        raise PipxError(f"{package} was already installed with pipx 😴")
    venv = Venv(venv_dir, python=python, verbose=verbose)
    venv.create_venv()
    try:
        venv.install_package(package_or_url)
    except PipxError:
        venv.remove_venv()
        raise

    if venv.get_package_version(package) is None:
        venv.remove_venv()
        raise PipxError(f"Could not find package {package}. Is the name correct?")
    binary_paths = venv.get_package_binary_paths(package)
    if not binary_paths:
        venv.remove_venv()
        raise PipxError("No binaries associated with this package")
    logging.info(f"new binaries: {', '.join(str(b.name) for b in binary_paths)}")
    symlink_package_binaries(local_bin_dir, binary_paths, package)
    print("done! ✨ 🌟 ✨")


def uninstall(venv_dir, package, local_bin_dir, verbose):
    if not venv_dir.exists():
        print(f"Nothing to uninstall for {package} 😴")
        return

    venv = Venv(venv_dir, verbose=verbose)
    installed_binaries = [b for b in venv.bin_path.iterdir()]
    for symlink in local_bin_dir.iterdir():
        for b in installed_binaries:
            if symlink.exists() and b.exists() and symlink.samefile(b):
                logging.info(f"removing symlink {str(symlink)}")
                symlink.unlink()

    rmdir(venv_dir)
    print(f"uninstalled {package}! ✨ 🌟 ✨")


def uninstall_all(pipx_local_venvs, local_bin_dir, verbose):
    for venv_dir in pipx_local_venvs.iterdir():
        package = venv_dir.name
        uninstall(venv_dir, package, local_bin_dir, verbose)


def get_fs_package_name(package):
    illegal = ["+", "#", "/", ":"]
    ret = ""
    for x in package:
        if x in illegal:
            ret += "_"
        else:
            ret += x
    return ret


def print_version():
    print("0.0.0.3")


def run_pipx_command(args):
    setup(args)
    verbose = args.verbose
    if "package" in args:
        package = args.package
        if urllib.parse.urlparse(package).scheme:
            raise PipxError(
                "Package must be a name. To install a "
                "package from a url, pass the --url flag."
            )
        if package == "pipx":
            print(f"isntalling pipx from url {INSTALL_PIPX_URL}")
            args.url = INSTALL_PIPX_URL
        if "url" in args:
            if urllib.parse.urlparse(args.url).scheme:
                if "#egg=" not in args.url:
                    args.url = args.url + f"#egg={package}"
            else:
                raise PipxError("Url was not a valid url")

        venv_dir = pipx_local_venvs / package
        logging.info(f"virtualenv location is {venv_dir}")

    if args.command == "install":
        package_or_url = args.url if "url" in args else package
        install(venv_dir, package, package_or_url, local_bin_dir, args.python, verbose)
    elif args.command == "upgrade":
        package_or_url = args.url if "url" in args else package
        upgrade(venv_dir, package, package_or_url, verbose)
    elif args.command == "list":
        list_packages(pipx_local_venvs)
    elif args.command == "uninstall":
        uninstall(venv_dir, package, local_bin_dir, verbose)
    elif args.command == "uninstall-all":
        uninstall_all(pipx_local_venvs, local_bin_dir, verbose)
    elif args.command == "upgrade-all":
        upgrade_all(pipx_local_venvs, verbose)
    else:
        raise PipxError(f"Unknown command {args.command}")


def run_ephemeral_binary(args, binary_args):
    binary = args.binary[0] if args.binary else None
    package = args.package if args.package else binary
    if package == "pipx":
        args.url = INSTALL_PIPX_URL
    verbose = args.verbose

    if not binary:
        get_command_parser().print_help()
        exit(1)

    if urllib.parse.urlparse(binary).scheme:
        logging.info("Detected url. Downloading and executing as a Python file.")
        # download and run directly
        r = requests.get(binary)
        try:
            subprocess.run([args.python, "-c", r.content])
        except KeyboardInterrupt:
            pass
        exit(0)
    elif which(binary):
        logging.warning(
            f"{binary} is already on your PATH and installed at "
            f"{which(binary)}. Downloading and "
            "running latest version anyway."
        )

    with tempfile.TemporaryDirectory(
        prefix=f"{get_fs_package_name(package)}_"
    ) as venv_dir:
        logging.info(f"virtualenv is temporary, its location is {venv_dir}")
        return download_and_run(
            Path(venv_dir), package, binary, binary_args, args.python, verbose
        )


def get_binary_parser(add_help):
    parser = argparse.ArgumentParser(add_help=add_help)

    if not add_help:
        parser.add_argument("--help", "-h", action="store_true")
    parser.add_argument(
        "binary",
        help="A Python package's binary to run or the pipx command to run. If binary,"
        "the PyPI package is assumed to have the same name.",
        nargs="*",
        type=str,
    )

    parser.add_argument(
        "--package",
        help="The package to install from PyPI that contains the binary. "
        "The package name default is the name of the provided binary.",
    )
    parser.add_argument(
        "--python",
        default="python3",
        help="The Python binary to associate the CLI binary with. Must be v3.3+.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Log additional output to the console",
    )
    parser.add_argument("--version", action="store_true", help="Show version")
    return parser


def get_command_parser():
    parser = argparse.ArgumentParser(
        usage="""
    %(prog)s [-h] [--package PACKAGE] [--python PYTHON] [-v] [--version] binary
    %(prog)s [-h] {install,upgrade,upgrade-all,uninstall,uninstall-all,list} ...
    """,
        description=textwrap.dedent(
            f"""
    Execute binaries from Python packages.

    Alternatively, safely install a package in a virtualenv with its binaries available globally.

    pipx will install a virtualenv for the package
    in {DEFAULT_PIPX_HOME}. Symlinks to binaries are placed in {DEFAULT_PIPX_BIN_DIR}.
    These locations can be overridden with the environment variables
    PIPX_HOME and PIPX_BIN_DIR, respectively.
    """
        ),
    )
    subparsers = parser.add_subparsers(
        dest="command", description="Get help for commands with pipx COMMAND --help"
    )
    p = subparsers.add_parser(
        "binary",
        help=("Run a binary with the given from an ephemral virtualenv"),
    )
    p.add_argument("--package")
    p.add_argument("--verbose", action="store_true")
    p.add_argument(
        "--python",
        default="python3",
        help="The Python binary to associate the CLI binary with. Must be v3.3+.",
    )

    p = subparsers.add_parser("install", help="Install a package")
    p.add_argument("package", help="package name")
    p.add_argument(
        "--url",
        help="Value paassed directly to `pip install ...`. "
        f"For example `--url {INSTALL_PIPX_URL}`",
    )
    p.add_argument("--verbose", action="store_true")
    p.add_argument(
        "--python",
        default="python3",
        help="The Python binary to associate the CLI binary with. Must be v3.3+.",
    )

    p = subparsers.add_parser("upgrade", help="Upgrade a package")
    p.add_argument("package")
    p.add_argument(
        "--url", help="Run `pip install -U URL` instead of `pip install -U PACKAGE`"
    )
    p.add_argument("--verbose", action="store_true")

    p = subparsers.add_parser(
        "upgrade-all",
        help="Upgrade all packages. "
        "Runs `pip install -U <pkgname>` for each package.",
    )
    p.add_argument("--verbose", action="store_true")

    p = subparsers.add_parser("uninstall", help="Uninstall a package")
    p.add_argument("package")
    p.add_argument("--verbose", action="store_true")

    p = subparsers.add_parser(
        "uninstall-all", help="Uninstall all package, including pipx"
    )
    p.add_argument("--verbose", action="store_true")

    p = subparsers.add_parser("list", help="List installed packages")
    p.add_argument("--verbose", action="store_true")

    return parser


def separate_pipx_and_binary_args(argv, pipx_commands):
    args = get_binary_parser(add_help=False).parse_args()
    if not args.binary and args.version:
        print_version()
        exit(0)
    index = argv.index(args.binary[0]) if args.binary else 0
    pipx_args = argv[1 : index + 1]
    binary_args = argv[index + 1 :]
    return (pipx_args, binary_args)


def args_have_command(pipx_commands):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="*")
    args = parser.parse_known_args()
    if args[0].command:
        return args[0].command[0] in pipx_commands
    else:
        return False


def setup(args):
    if "version" in args and args.version:
        print_version()
        exit(0)

    if "verbose" in args and args.verbose:
        logging.basicConfig(
            level=logging.DEBUG, format="pipx (%(funcName)s:%(lineno)d): %(message)s"
        )
    else:
        logging.basicConfig(level=logging.WARNING, format="%(message)s")

    mkdir(pipx_local_venvs)
    mkdir(local_bin_dir)


def cli():
    """Entry point from command line"""
    pipx_commands = [
        "install",
        "upgrade",
        "upgrade-all",
        "uninstall",
        "uninstall-all",
        "list",
    ]

    try:
        if args_have_command(pipx_commands):
            args = get_command_parser().parse_args()
            setup(args)
            run_pipx_command(args)
        else:
            pipx_args, binary_args = separate_pipx_and_binary_args(
                sys.argv, pipx_commands
            )
            args = get_binary_parser(add_help=True).parse_args(pipx_args)
            setup(args)
            exit(run_ephemeral_binary(args, binary_args))
    except PipxError as e:
        exit(e)


if __name__ == "__main__":
    cli()
