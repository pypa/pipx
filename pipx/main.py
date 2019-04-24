#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import logging
import os
import shlex
import sys
import textwrap
import urllib.parse
from typing import Dict, List, Tuple

from . import commands
from .constants import (
    DEFAULT_PYTHON,
    LOCAL_BIN_DIR,
    DEFAULT_PIPX_HOME,
    DEFAULT_PIPX_BIN_DIR,
    PIPX_LOCAL_VENVS,
    PIPX_VENV_CACHEDIR,
    TEMP_VENV_EXPIRATION_THRESHOLD_DAYS,
)
from .util import PipxError, mkdir


__version__ = "0.13.1.0"


def print_version() -> None:
    print(__version__)


SPEC_HELP = textwrap.dedent(
    """The package name or specific installation source passed to pip.
    Runs `pip install -U SPEC`.
    For example `--spec mypackage==2.0.0` or `--spec  git+https://github.com/user/repo.git@branch`
    """
)
PIPX_DESCRIPTION = textwrap.dedent(
    f"""
Install and execute binaries from Python packages.

Binaries can either be installed globally into isolated Virtual Environments
or run directly in an temporary Virtual Environment.

Virtual Environment location is {str(PIPX_LOCAL_VENVS)}.
Symlinks to binaries are placed in {str(LOCAL_BIN_DIR)}.
These locations can be overridden with the environment variables
PIPX_HOME and PIPX_BIN_DIR, respectively. (Virtual Environments will
be installed to $PIPX_HOME/venvs)
"""
)


INSTALL_DESCRIPTION = f"""
The install command is the preferred way to globally install binaries
from python packages on your system. It creates an isolated virtual
environment for the package, then ensures the package's binaries are
accessible on your $PATH.

The result: binaries you can run from anywhere, located in packages
you can cleanly upgrade or uninstall. Guaranteed to not have
dependency version conflicts or interfere with your OS's python
packages. 'sudo' is not required to do this.

pipx install PACKAGE
pipx install --python PYTHON PACKAGE
pipx install --spec VCS_URL PACKAGE
pipx install --spec ZIP_FILE PACKAGE
pipx install --spec TAR_GZ_FILE PACKAGE

The argument to `--spec` is passed directly to `pip install`.

The default virtual environment location is {DEFAULT_PIPX_HOME}
and can be overridden by setting the environment variable `PIPX_HOME`
 (Virtual Environments will be installed to `$PIPX_HOME/venvs`).

The default binary location is {DEFAULT_PIPX_BIN_DIR} and can be
overridden by setting the environment variable `PIPX_BIN_DIR`.
"""


class LineWrapRawTextHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def _split_lines(self, text, width):
        text = self._whitespace_matcher.sub(" ", text).strip()
        return textwrap.wrap(text, width)


def get_pip_args(parsed_args: Dict):
    pip_args: List[str] = []
    if parsed_args.get("index_url"):
        pip_args += ["--index-url", parsed_args["index_url"]]

    if parsed_args.get("editable"):
        pip_args += ["--editable"]

    if parsed_args.get("pip_args"):
        pip_args += shlex.split(parsed_args.get("pip_args", ""))
    return pip_args


def get_venv_args(parsed_args: Dict):
    venv_args: List[str] = []
    if parsed_args.get("system_site_packages"):
        venv_args += ["--system-site-packages"]
    return venv_args


def run_pipx_command(args, binary_args: List[str]):
    setup(args)
    verbose = args.verbose if "verbose" in args else False
    pip_args = get_pip_args(vars(args))
    venv_args = get_venv_args(vars(args))

    if "package" in args:
        package = args.package
        if urllib.parse.urlparse(package).scheme:
            raise PipxError("Package cannot be a url")

        if "spec" in args and args.spec is not None:
            if urllib.parse.urlparse(args.spec).scheme:
                if "#egg=" not in args.spec:
                    args.spec = args.spec + f"#egg={package}"

        venv_dir = PIPX_LOCAL_VENVS / package
        logging.info(f"Virtual Environment location is {venv_dir}")

    if args.command == "run":
        package_or_url = (
            args.spec if ("spec" in args and args.spec is not None) else args.binary
        )
        use_cache = not args.no_cache
        return commands.run(
            args.binary,
            package_or_url,
            binary_args,
            args.python,
            pip_args,
            venv_args,
            args.pypackages,
            verbose,
            use_cache,
        )
    elif args.command == "install":
        package_or_url = (
            args.spec if ("spec" in args and args.spec is not None) else package
        )
        commands.install(
            venv_dir,
            package,
            package_or_url,
            LOCAL_BIN_DIR,
            args.python,
            pip_args,
            venv_args,
            verbose,
            force=args.force,
            include_deps=args.include_deps,
        )
    elif args.command == "inject":
        if not args.include_binaries and args.include_deps:
            raise PipxError(
                "Cannot pass --include-deps if --use_binaries is not passed as well"
            )
        for dep in args.dependencies:
            commands.inject(
                venv_dir,
                dep,
                pip_args,
                verbose=verbose,
                include_binaries=args.include_binaries,
                include_deps=args.include_deps,
            )
    elif args.command == "upgrade":
        package_or_url = (
            args.spec if ("spec" in args and args.spec is not None) else package
        )
        commands.upgrade(
            venv_dir,
            package,
            package_or_url,
            pip_args,
            verbose,
            upgrading_all=False,
            include_deps=args.include_deps,
        )
    elif args.command == "list":
        commands.list_packages(PIPX_LOCAL_VENVS)
    elif args.command == "uninstall":
        commands.uninstall(venv_dir, package, LOCAL_BIN_DIR, verbose)
    elif args.command == "uninstall-all":
        commands.uninstall_all(PIPX_LOCAL_VENVS, LOCAL_BIN_DIR, verbose)
    elif args.command == "upgrade-all":
        commands.upgrade_all(
            PIPX_LOCAL_VENVS,
            pip_args,
            verbose,
            include_deps=args.include_deps,
            skip=args.skip,
        )
    elif args.command == "reinstall-all":
        commands.reinstall_all(
            PIPX_LOCAL_VENVS,
            LOCAL_BIN_DIR,
            args.python,
            pip_args,
            venv_args,
            verbose,
            args.include_deps,
            skip=args.skip,
        )
    elif args.command == "runpip":
        if not venv_dir:
            raise PipxError("developer error: venv dir is not defined")
        commands.run_pip(package, venv_dir, binary_args, args.verbose)
    elif args.command == "ensurepath":
        paths = os.getenv("PATH", "").split(os.pathsep)
        path_good = str(LOCAL_BIN_DIR) in paths
        if not path_good or args.force:
            commands.ensurepath(LOCAL_BIN_DIR)
        else:
            print(
                "Your PATH looks like it already is set up for pipx. Pass `--force` to modify the PATH."
            )
    else:
        raise PipxError(f"Unknown command {args.command}")


def add_pip_venv_args(parser):
    parser.add_argument(
        "--system-site-packages",
        action="store_true",
        help="Give the virtual environment access to the system site-packages dir.",
    )
    parser.add_argument("--index-url", "-i", help="Base URL of Python Package Index")
    parser.add_argument(
        "--editable",
        "-e",
        help="Install a project in editable mode",
        action="store_true",
    )
    parser.add_argument(
        "--pip-args",
        help="Arbitrary pip arguments to pass directly to pip install/upgrade commands",
    )


def add_include_deps(parser):
    parser.add_argument(
        "--include-deps",
        help="Include binaries of dependent packages",
        action="store_true",
    )


def get_command_parser():
    parser = argparse.ArgumentParser(
        formatter_class=LineWrapRawTextHelpFormatter, description=PIPX_DESCRIPTION
    )

    subparsers = parser.add_subparsers(
        dest="command", description="Get help for commands with pipx COMMAND --help"
    )

    p = subparsers.add_parser(
        "install",
        help="Install a package",
        formatter_class=LineWrapRawTextHelpFormatter,
        description=INSTALL_DESCRIPTION,
    )
    p.add_argument("package", help="package name")
    p.add_argument("--spec", help=SPEC_HELP)
    add_include_deps(p)
    p.add_argument("--verbose", action="store_true")
    p.add_argument(
        "--force",
        action="store_true",
        help="Install even when the package has already been installed",
    )
    p.add_argument(
        "--python",
        default=DEFAULT_PYTHON,
        help=(
            "The Python executable used to create the Virtual Environment and run the "
            "associated binary/binaries. Must be v3.3+."
        ),
    )
    add_pip_venv_args(p)

    p = subparsers.add_parser(
        "inject",
        help="Install packages into an existing Virtual Environment",
        description="Installs packages to an existing pipx-managed virtual environment.",
    )
    p.add_argument(
        "package",
        help="Name of the existing pipx-managed Virtual Environment to inject into",
    )
    p.add_argument(
        "dependencies",
        nargs="+",
        help="the packages to inject into the Virtual Environment",
    )
    p.add_argument(
        "--include-binaries",
        action="store_true",
        help="Add binaries from the injected packages onto your PATH",
    )
    add_include_deps(p)
    add_pip_venv_args(p)
    p.add_argument("--verbose", action="store_true")

    p = subparsers.add_parser(
        "upgrade",
        help="Upgrade a package",
        description="Upgrade a package in a pipx-managed Virtual Environment by running 'pip install --upgrade PACKAGE'",
    )
    p.add_argument("package")
    p.add_argument("--spec", help=SPEC_HELP)
    add_include_deps(p)
    add_pip_venv_args(p)
    p.add_argument("--verbose", action="store_true")

    p = subparsers.add_parser(
        "upgrade-all",
        help="Upgrade all packages. "
        "Runs `pip install -U <pkgname>` for each package.",
        description="Upgrades all packages within their virtual environments by running 'pip install --upgrade PACKAGE'",
    )

    add_include_deps(p)
    add_pip_venv_args(p)
    p.add_argument("--skip", nargs="+", default=[], help="skip these packages")
    p.add_argument("--verbose", action="store_true")

    p = subparsers.add_parser(
        "uninstall",
        help="Uninstall a package",
        description="Uninstalls a pipx-managed Virtual Environment by deleting it and any files that point to its binaries.",
    )
    p.add_argument("package")
    p.add_argument("--verbose", action="store_true")

    p = subparsers.add_parser(
        "uninstall-all",
        help="Uninstall all packages",
        description="Uninstall all pipx-managed packages",
    )
    p.add_argument("--verbose", action="store_true")

    p = subparsers.add_parser(
        "reinstall-all",
        formatter_class=LineWrapRawTextHelpFormatter,
        help="Reinstall all packages with a different Python executable",
        description=textwrap.dedent(
            """
        Reinstalls all packages using a different version of Python.

        Packages are uninstalled, then installed with pipx install PACKAGE.
        This is useful if you upgraded to a new version of Python and want
        all your packages to use the latest as well.

        If you originally installed a package from a source other than PyPI,
        this command may behave in unexpected ways since it will reinstall from PyPI.

        """
        ),
    )
    p.add_argument("python")
    add_include_deps(p)
    add_pip_venv_args(p)
    p.add_argument("--skip", nargs="+", default=[], help="skip these packages")
    p.add_argument("--verbose", action="store_true")

    p = subparsers.add_parser(
        "list",
        help="List installed packages",
        description="List packages and binariess installed with pipx",
    )
    p.add_argument("--verbose", action="store_true")

    p = subparsers.add_parser(
        "run",
        formatter_class=LineWrapRawTextHelpFormatter,
        help=(
            "Download the latest version of a package to a temporary virtual environment, "
            "then run a binary from it. Also compatible with local `__pypackages__` "
            "directory (experimental)."
        ),
        description=textwrap.dedent(
            f"""
        Download the latest version of a package to a temporary virtual environment,
        then run a binary from it. The environment will be cached
        and re-used for up to {TEMP_VENV_EXPIRATION_THRESHOLD_DAYS} days. This
        means subsequent calls to 'run' for the same package will be faster
        since they can re-use the cached Virtual Environment.

        In support of PEP 582 'run' will use binaries found in a local __pypackages__
         directory, if present. Please note that this behavior is experimental,
         and is a acts as a companion tool to pythonloc. It may be modified or
         removed in the future. See https://github.com/cs01/pythonloc.
        """
        ),
    )
    p.add_argument(
        "--no-cache",
        action="store_true",
        help="Do not re-use cached virtual environment if it exists",
    )
    p.add_argument("binary", help="binary/package name")
    p.add_argument(
        "binary_args",
        nargs="*",
        help="arguments passed to the binary when it is invoked",
        default=[],
    )
    p.add_argument(
        "--pypackages",
        action="store_true",
        help="Require binary to be run from local __pypackages__ directory",
    )
    p.add_argument("--spec", help=SPEC_HELP)
    p.add_argument("--verbose", action="store_true")
    p.add_argument(
        "--python",
        default=DEFAULT_PYTHON,
        help="The Python version to run package's CLI binary with. Must be v3.3+.",
    )
    add_pip_venv_args(p)

    p = subparsers.add_parser(
        "runpip",
        help="Run pip in an existing pipx-managed Virtual Environment",
        description="Run pip in an existing pipx-managed Virtual Environment",
    )
    p.add_argument(
        "package",
        help="Name of the existing pipx-managed Virtual Environment to run pip in",
    )
    p.add_argument("pipargs", nargs="*", help="Arguments to forward to pip command")
    p.add_argument("--verbose", action="store_true")

    p = subparsers.add_parser(
        "ensurepath",
        help="Deprecated, will be removed in a future release. Use `userpath` instead.",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help=(
            "Add text to your shell's config file even if it looks like your "
            f"PATH already has {str(LOCAL_BIN_DIR)}"
        ),
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    return parser


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

    mkdir(PIPX_LOCAL_VENVS)
    mkdir(LOCAL_BIN_DIR)
    mkdir(PIPX_VENV_CACHEDIR)

    old_pipx_venv_location = PIPX_LOCAL_VENVS / "pipx-app"
    if old_pipx_venv_location.exists():
        logging.warning(
            "A virtual environment for pipx was detected at "
            f"{str(old_pipx_venv_location)}. The 'pipx-app' package has been renamed "
            "back to 'pipx' (https://github.com/pipxproject/pipx/issues/82)."
        )


def split_run_argv(argv: List[str]) -> Tuple[List[str], List[str]]:
    """If 'run' command is used, split between args passed to pipx and args
    to be forwarded to binary
    """
    args_to_parse = argv[1:]
    binary_args: List[str] = []

    if len(argv) >= 2:
        if argv[1] == "runpip":
            package_index = argv.index("runpip") + 1
            return argv[1 : package_index + 1], argv[package_index + 1 :]

        if argv[1] == "run":
            start = 2
            for i, arg in enumerate(argv[start:]):
                if not arg.startswith("-"):
                    offset = start + i + 1
                    args_to_parse = argv[1:offset]
                    binary_args = argv[offset:]
                    break
    return args_to_parse, binary_args


def cli():
    """Entry point from command line"""
    try:
        args_to_parse, binary_args = split_run_argv(sys.argv)
        parser = get_command_parser()
        parsed_pipx_args = parser.parse_args(args_to_parse)
        setup(parsed_pipx_args)
        if not parsed_pipx_args.command:
            parser.print_help()
            exit(1)
        exit(run_pipx_command(parsed_pipx_args, binary_args))
    except PipxError as e:
        exit(e)
    except KeyboardInterrupt:
        exit(1)


if __name__ == "__main__":
    cli()
