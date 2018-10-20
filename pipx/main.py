#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

try:
    WindowsError
except NameError:
    IS_WIN = False
else:
    IS_WIN = True

DEFAULT_PYTHON = "python3.exe" if IS_WIN else "python3"
DEFAULT_PIPX_HOME = Path.home() / ".local/pipx/venvs"
DEFAULT_PIPX_BIN_DIR = Path.home() / ".local/bin"
pipx_local_venvs = Path(os.environ.get("PIPX_HOME", DEFAULT_PIPX_HOME)).resolve()
local_bin_dir = Path(os.environ.get("PIPX_BIN_DIR", DEFAULT_PIPX_BIN_DIR)).resolve()
INSTALL_PIPX_URL = "git+https://github.com/cs01/pipx.git"
INSTALL_PIPX_CMD = (
    "curl https://raw.githubusercontent.com/cs01/pipx/master/get-pipx.py | python3"
)
SPEC_HELP = (
    "Run `pip install -U SPEC` instead of `pip install -U PACKAGE`"
    f"For example `--from {INSTALL_PIPX_URL}` or `--from mypackage==2.0.0.`"
)
PIPX_DESCRIPTION = textwrap.dedent(
    f"""
Execute binaries from Python packages.

Binaries can either be run directly or installed globally into isolated venvs.

venv location is {str(pipx_local_venvs)}.
Symlinks to binaries are placed in {str(local_bin_dir)}.
These locations can be overridden with the environment variables
PIPX_HOME and PIPX_BIN_DIR, respectively.
"""
)
PIPX_USAGE = """
    %(prog)s [--spec SPEC] [--python PYTHON] BINARY [BINARY-ARGS]
    %(prog)s {install,upgrade,upgrade-all,uninstall,uninstall-all,list} [--help]"""


class PipxError(Exception):
    pass


class Venv:
    def __init__(self, path, *, verbose=False, python=DEFAULT_PYTHON):
        self.root = path
        self._python = python
        self.bin_path = path / "bin"
        self.pip_path = self.bin_path / ("pip" if not IS_WIN else "pip.exe")
        self.python_path = self.bin_path / ("python" if not IS_WIN else "python.exe")
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
            import os
            from pathlib import Path

            dist = pkg_resources.get_distribution("{package}")
            bin_path = "{self.bin_path}"
            binaries = set()
            for _, d in pkg_resources.get_entry_map(dist).items():
                for binary in d:
                    binaries.add(binary)

            if dist.has_metadata('RECORD'):
                for line in dist.get_metadata_lines('RECORD'):
                    binary = line.split(',')[0]
                    path = Path(dist.location) / binary
                    if path.parent.samefile(bin_path):
                        binaries.add(Path(binary).name)

            if dist.has_metadata('installed-files.txt'):
                for line in dist.get_metadata_lines('installed-files.txt'):
                    binary = line.split(',')[0]
                    path = Path(dist.location) / binary
                    if path.parent.samefile(bin_path):
                        binaries.add(Path(binary).name)
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
                f"⚠️  {binary} is already on your PATH at "
                f"{Path(which(binary)).resolve()}. Not creating new symlink at {str(symlink_path)}"
            )
        elif symlink_path.exists():
            logging.warning(
                f"⚠️  File exists at {str(symlink_path)} and points to {symlink_path.resolve()}. Not creating."
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
        f"venvs are in {str(pipx_local_venvs)}, symlinks to binaries are in {str(local_bin_dir)}"
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
                f"{package} is not installed in the venv {str(d)}"
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
            f"package {package} {version}, symlinks to binaries available: {', '.join(symlinked_binaries)}{unavailable}"
        )
        logging.info(f"virtualenv: {str(d)}, python executable: {python_path}")


def get_valid_bin_symlinks_for_package(venv_bin_dir, local_bin_dir):
    symlinks = []
    for b in local_bin_dir.iterdir():
        if (venv_bin_dir / b.name).exists():
            symlinks.append(b.name)
    return symlinks


def upgrade(venv_dir, package, package_or_url, verbose):
    if not venv_dir.is_dir():
        raise PipxError(
            f"Package is not installed. Expected to find {str(venv_dir)}, "
            "but it does not exist."
        )
    venv = Venv(venv_dir, verbose=verbose)
    venv.upgrade_package(package_or_url)
    binary_paths = venv.get_package_binary_paths(package)
    symlink_package_binaries(local_bin_dir, binary_paths, package)
    print(f"upgraded package {package} to latest version (location: {str(venv_dir)})")


def upgrade_all(pipx_local_venvs, verbose):
    for venv_dir in pipx_local_venvs.iterdir():
        package = venv_dir.name
        if package == "pipx":
            package_or_url = INSTALL_PIPX_URL
        else:
            package_or_url = package
        upgrade(venv_dir, package, package_or_url, verbose)


def install(venv_dir, package, package_or_url, local_bin_dir, python, verbose):
    venv = Venv(venv_dir, python=python, verbose=verbose)
    if venv_dir.exists():
        pass
    else:
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
        binary = which(package)
        if binary:
            print(
                f"⚠️  Note: '{binary}' still exists on your system and is on your PATH"
            )
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


def reinstall_all(pipx_local_venvs, local_bin_dir, python, verbose):
    for venv_dir in pipx_local_venvs.iterdir():
        package = venv_dir.name
        uninstall(venv_dir, package, local_bin_dir, verbose)

        package_or_url = package
        install(venv_dir, package, package_or_url, local_bin_dir, python, verbose)


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
    print("0.0.0.9")


def run_pipx_command(args):
    setup(args)
    verbose = args.verbose
    if "package" in args:
        package = args.package
        if urllib.parse.urlparse(package).scheme:
            raise PipxError("Package cannot be a url")
        if package == "pipx":
            logging.warning(f"using url {INSTALL_PIPX_URL} for pipx installation")
            args.spec = INSTALL_PIPX_URL
        if "spec" in args and args.spec is not None:
            if urllib.parse.urlparse(args.spec).scheme:
                if "#egg=" not in args.spec:
                    args.spec = args.spec + f"#egg={package}"

        venv_dir = pipx_local_venvs / package
        logging.info(f"virtualenv location is {venv_dir}")

    if args.command == "install":
        package_or_url = (
            args.spec if ("spec" in args and args.spec is not None) else package
        )
        install(venv_dir, package, package_or_url, local_bin_dir, args.python, verbose)
    elif args.command == "upgrade":
        package_or_url = (
            args.spec if ("spec" in args and args.spec is not None) else package
        )
        upgrade(venv_dir, package, package_or_url, verbose)
    elif args.command == "list":
        list_packages(pipx_local_venvs)
    elif args.command == "uninstall":
        uninstall(venv_dir, package, local_bin_dir, verbose)
    elif args.command == "uninstall-all":
        uninstall_all(pipx_local_venvs, local_bin_dir, verbose)
        print(f"To reinstall pipx, run '{INSTALL_PIPX_CMD}'")
    elif args.command == "upgrade-all":
        upgrade_all(pipx_local_venvs, verbose)
    elif args.command == "reinstall-all":
        reinstall_all(pipx_local_venvs, local_bin_dir, args.python, verbose)
    else:
        raise PipxError(f"Unknown command {args.command}")


def run_ephemeral_binary(args, binary_args):
    if not args.binary:
        get_command_parser().print_help()
        exit(1)
    binary = args.binary[0]
    package_or_url = args.spec if args.spec else binary
    if package_or_url == "pipx":
        logging.warning(f"using url {INSTALL_PIPX_URL} for pipx installation")
        package_or_url = INSTALL_PIPX_URL
    verbose = args.verbose

    if urllib.parse.urlparse(binary).scheme:
        if not binary.endswith(".py"):
            exit(
                "pipx will only execute binaries from the internet directly if "
                "they end with '.py'. To run from an SVN, try pipx --from URL BINARY"
            )
        logging.info("Detected url. Downloading and executing as a Python file.")
        # download and run directly
        r = requests.get(binary)
        try:
            exit(subprocess.run([args.python, "-c", r.content]).returncode)
        except KeyboardInterrupt:
            pass
        exit(0)
    elif which(binary):
        logging.warning(
            f"⚠️  {binary} is already on your PATH and installed at "
            f"{which(binary)}. Downloading and "
            "running anyway."
        )

    with tempfile.TemporaryDirectory(
        prefix=f"{get_fs_package_name(package_or_url)}_"
    ) as venv_dir:
        logging.info(f"virtualenv is temporary, its location is {venv_dir}")
        return download_and_run(
            Path(venv_dir), package_or_url, binary, binary_args, args.python, verbose
        )


def get_binary_parser(add_help):
    parser = argparse.ArgumentParser(
        add_help=add_help,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage=PIPX_USAGE,
        description=PIPX_DESCRIPTION,
    )

    if not add_help:
        parser.add_argument("--help", "-h", action="store_true")
    parser.add_argument(
        "binary",
        help="A Python package's binary to run or the pipx command to run. If binary,"
        "the PyPI package is assumed to have the same name.",
        nargs="*",
        type=str,
    )

    parser.add_argument("--spec", help=SPEC_HELP)
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
        formatter_class=argparse.RawTextHelpFormatter,
        usage=PIPX_USAGE,
        description=PIPX_DESCRIPTION,
    )

    subparsers = parser.add_subparsers(
        dest="command", description="Get help for commands with pipx COMMAND --help"
    )
    p = subparsers.add_parser(
        "binary", help=("Run a binary with the given from an ephemral virtualenv")
    )
    p.add_argument("--spec", help=SPEC_HELP)
    p.add_argument("--verbose", action="store_true")
    p.add_argument(
        "--python",
        default="python3",
        help="The Python binary to associate the CLI binary with. Must be v3.3+.",
    )

    p = subparsers.add_parser("install", help="Install a package")
    p.add_argument("package", help="package name")
    p.add_argument("--spec", help=SPEC_HELP)
    p.add_argument("--verbose", action="store_true")
    p.add_argument(
        "--python",
        default="python3",
        help="The Python binary to associate the CLI binary with. Must be v3.3+.",
    )

    p = subparsers.add_parser("upgrade", help="Upgrade a package")
    p.add_argument("package")
    p.add_argument("--spec", help=SPEC_HELP)
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
        "uninstall-all", help="Uninstall all packages, including pipx"
    )
    p.add_argument("--verbose", action="store_true")

    p = subparsers.add_parser(
        "reinstall-all",
        help="Reinstall all packages with a different Python executable",
    )
    p.add_argument("python")
    p.add_argument("--verbose", action="store_true")

    p = subparsers.add_parser("list", help="List installed packages")
    p.add_argument("--verbose", action="store_true")

    return parser


def separate_pipx_and_binary_args(argv, pipx_commands):
    args = get_binary_parser(add_help=False).parse_args()
    if not args.binary and args.version:
        print_version()
        exit(0)
    if args.binary:
        index = argv.index(args.binary[0])
        pipx_args = argv[1 : index + 1]
        binary_args = argv[index + 1 :]
    else:
        # there was no binary, so all args are for pipx
        pipx_args = argv[1:]
        binary_args = []
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
        "reinstall-all",
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
