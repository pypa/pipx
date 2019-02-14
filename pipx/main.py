#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import logging
import os
import sys
from .constants import (
    LOCAL_BIN_DIR,
    PIPX_LOCAL_VENVS,
    PIPX_PACKAGE_NAME,
    PIPX_VENV_CACHEDIR,
    DEFAULT_PYTHON,
)
from .util import mkdir, PipxError
from . import commands
import shlex
from typing import Dict, List, Tuple
import textwrap
import urllib.parse

__version__ = "0.12.1.0"


def print_version() -> None:
    print(__version__)


SPEC_HELP = (
    "The package name or specific installation source. "
    "Runs `pip install -U SPEC`. "
    f"For example `--spec {PIPX_PACKAGE_NAME}` or `--spec mypackage==2.0.0.`"
)
PIPX_DESCRIPTION = textwrap.dedent(
    f"""
Install and execute binaries from Python packages.

Binaries can either be installed globally into isolated Virtual Environments
or run directly in an ephemeral Virtual Environment.

venv location is {str(PIPX_LOCAL_VENVS)}.
Symlinks to binaries are placed in {str(LOCAL_BIN_DIR)}.
These locations can be overridden with the environment variables
PIPX_HOME and PIPX_BIN_DIR, respectively. (venvs will be installed to
$PIPX_HOME/venvs)
"""
)


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
        logging.info(f"virtualenv location is {venv_dir}")

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
        )
    elif args.command == "inject":
        for dep in args.dependencies:
            commands.inject(venv_dir, dep, pip_args, verbose)
    elif args.command == "upgrade":
        package_or_url = (
            args.spec if ("spec" in args and args.spec is not None) else package
        )
        commands.upgrade(
            venv_dir, package, package_or_url, pip_args, verbose, upgrading_all=False
        )
    elif args.command == "list":
        commands.list_packages(PIPX_LOCAL_VENVS)
    elif args.command == "uninstall":
        commands.uninstall(venv_dir, package, LOCAL_BIN_DIR, verbose)
    elif args.command == "uninstall-all":
        commands.uninstall_all(PIPX_LOCAL_VENVS, LOCAL_BIN_DIR, verbose)
    elif args.command == "upgrade-all":
        commands.upgrade_all(PIPX_LOCAL_VENVS, pip_args, verbose)
    elif args.command == "reinstall-all":
        commands.reinstall_all(
            PIPX_LOCAL_VENVS, LOCAL_BIN_DIR, args.python, pip_args, venv_args, verbose
        )
    elif args.command == "ensurepath":
        if os.getenv("PATH") is not None:
            path_good = str(LOCAL_BIN_DIR) in (os.getenv("PATH") or "")
        if not path_good or (path_good and args.force):
            commands.ensurepath(LOCAL_BIN_DIR)
        else:
            print(
                "Your PATH looks like it already is set up for pipx. "
                "Pass `--force` to modify the PATH."
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


def get_command_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter, description=PIPX_DESCRIPTION
    )

    subparsers = parser.add_subparsers(
        dest="command", description="Get help for commands with pipx COMMAND --help"
    )

    p = subparsers.add_parser("install", help="Install a package")
    p.add_argument("package", help="package name")
    p.add_argument("--spec", help=SPEC_HELP)
    p.add_argument("--verbose", action="store_true")
    p.add_argument(
        "--force",
        action="store_true",
        help="Install even when the package has already been installed",
    )
    p.add_argument(
        "--python",
        default=DEFAULT_PYTHON,
        help="The Python binary to associate the CLI binary with. Must be v3.3+.",
    )
    add_pip_venv_args(p)

    p = subparsers.add_parser(
        "inject", help="Install packages into an existing virtualenv"
    )
    p.add_argument(
        "package", help="Name of the existing pipx-managed virtualenv to inject into"
    )
    p.add_argument(
        "dependencies", nargs="+", help="the packages to inject into the virtualenv"
    )
    p.add_argument("--verbose", action="store_true")

    p = subparsers.add_parser("upgrade", help="Upgrade a package")
    p.add_argument("package")
    p.add_argument("--spec", help=SPEC_HELP)
    p.add_argument("--verbose", action="store_true")
    add_pip_venv_args(p)

    p = subparsers.add_parser(
        "upgrade-all",
        help="Upgrade all packages. "
        "Runs `pip install -U <pkgname>` for each package.",
    )
    p.add_argument("--verbose", action="store_true")
    add_pip_venv_args(p)

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
    add_pip_venv_args(p)

    p = subparsers.add_parser("list", help="List installed packages")
    p.add_argument("--verbose", action="store_true")

    p = subparsers.add_parser(
        "run",
        help="Download latest version of a package to temporary directory, "
        "then run a binary from it. Temp dir is removed after execution is finished.",
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
    p.add_argument("--spec", help=SPEC_HELP)
    p.add_argument("--verbose", action="store_true")
    p.add_argument(
        "--python",
        default=DEFAULT_PYTHON,
        help="The Python version to run package's CLI binary with. Must be v3.3+.",
    )
    add_pip_venv_args(p)

    p = subparsers.add_parser(
        "ensurepath",
        help=(
            f"Ensure {str(LOCAL_BIN_DIR)} is on your PATH environment variable"
            "by modifying your shell's configuration file."
        ),
    )
    p.add_argument(
        "--force",
        action="store_true",
        help=(
            f"Add text to your shell's config file even if it looks like your "
            "PATH already has {str(LOCAL_BIN_DIR)}"
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


if __name__ == "__main__":
    cli()
