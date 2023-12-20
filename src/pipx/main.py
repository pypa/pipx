# PYTHON_ARGCOMPLETE_OK

"""The command line interface to pipx"""

import argparse
import logging
import logging.config
import os
import re
import shlex
import sys
import textwrap
import time
import urllib.parse
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import argcomplete
import platformdirs
from packaging.utils import canonicalize_name

import pipx.constants
from pipx import commands, constants
from pipx.animate import hide_cursor, show_cursor
from pipx.colors import bold, green
from pipx.constants import MINIMUM_PYTHON_VERSION, WINDOWS, ExitCode
from pipx.emojis import hazard
from pipx.interpreter import DEFAULT_PYTHON, find_py_launcher_python
from pipx.util import PipxError, mkdir, pipx_wrap, rmdir
from pipx.venv import VenvContainer
from pipx.version import __version__

logger = logging.getLogger(__name__)

VenvCompleter = Callable[[str], List[str]]


def print_version() -> None:
    print(__version__)


def prog_name() -> str:
    try:
        prog = os.path.basename(sys.argv[0])
        if prog == "__main__.py":
            return f"{sys.executable} -m pipx"
        else:
            return prog
    except Exception:
        pass
    return "pipx"


SPEC_HELP = textwrap.dedent(
    """\
    The package name or specific installation source passed to pip.
    Runs `pip install -U SPEC`.
    For example `--spec mypackage==2.0.0` or `--spec  git+https://github.com/user/repo.git@branch`
    """
)

PIPX_DESCRIPTION = textwrap.dedent(
    f"""
    Install and execute apps from Python packages.

    Binaries can either be installed globally into isolated Virtual Environments
    or run directly in a temporary Virtual Environment.

    Virtual Environment location is {str(constants.PIPX_LOCAL_VENVS)}.
    Symlinks to apps are placed in {str(constants.LOCAL_BIN_DIR)}.
    Symlinks to manual pages are placed in {str(constants.LOCAL_MAN_DIR)}.

    """
)
PIPX_DESCRIPTION += pipx_wrap(
    """
    optional environment variables:
      PIPX_HOME             Overrides default pipx location. Virtual Environments will be installed to $PIPX_HOME/venvs.
      PIPX_BIN_DIR          Overrides location of app installations. Apps are symlinked or copied here.
      PIPX_MAN_DIR          Overrides location of manual pages installations. Manual pages are symlinked or copied here.
      PIPX_DEFAULT_PYTHON   Overrides default python used for commands.
      USE_EMOJI             Overrides emoji behavior. Default value varies based on platform.
    """,
    subsequent_indent=" " * 24,  # match the indent of argparse options
    keep_newlines=True,
)

DOC_DEFAULT_PYTHON = os.getenv("PIPX__DOC_DEFAULT_PYTHON", DEFAULT_PYTHON)

INSTALL_DESCRIPTION = textwrap.dedent(
    f"""
    The install command is the preferred way to globally install apps
    from python packages on your system. It creates an isolated virtual
    environment for the package, then ensures the package's apps are
    accessible on your $PATH. The package's manual pages installed in
    share/man/man[1-9] can be viewed with man on an operating system where
    it is available and the path in the environment variable `PIPX_MAN_DIR`
    (default: {constants.DEFAULT_PIPX_MAN_DIR}) is in the man search path
    ($MANPATH).

    The result: apps you can run from anywhere, located in packages
    you can cleanly upgrade or uninstall. Guaranteed to not have
    dependency version conflicts or interfere with your OS's python
    packages. 'sudo' is not required to do this.

    pipx install PACKAGE_NAME ...
    pipx install --python PYTHON PACKAGE_NAME
    pipx install VCS_URL
    pipx install ./LOCAL_PATH
    pipx install ZIP_FILE
    pipx install TAR_GZ_FILE

    The PACKAGE_SPEC argument is passed directly to `pip install`.

    The default virtual environment location is {constants.DEFAULT_PIPX_HOME}
    and can be overridden by setting the environment variable `PIPX_HOME`
    (Virtual Environments will be installed to `$PIPX_HOME/venvs`).

    The default app location is {constants.DEFAULT_PIPX_BIN_DIR} and can be
    overridden by setting the environment variable `PIPX_BIN_DIR`.

    The default manual pages location is {constants.DEFAULT_PIPX_MAN_DIR} and
    can be overridden by setting the environment variable `PIPX_MAN_DIR`.

    The default python executable used to install a package is
    {DOC_DEFAULT_PYTHON} and can be overridden
    by setting the environment variable `PIPX_DEFAULT_PYTHON`.
    """
)


class LineWrapRawTextHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def _split_lines(self, text: str, width: int) -> List[str]:
        text = self._whitespace_matcher.sub(" ", text).strip()
        return textwrap.wrap(text, width)


class InstalledVenvsCompleter:
    def __init__(self, venv_container: VenvContainer) -> None:
        self.packages = [str(p.name) for p in sorted(venv_container.iter_venv_dirs())]

    def use(self, prefix: str, **kwargs: Any) -> List[str]:
        return [f"{prefix}{x[len(prefix):]}" for x in self.packages if x.startswith(canonicalize_name(prefix))]


def get_pip_args(parsed_args: Dict[str, str]) -> List[str]:
    pip_args: List[str] = []
    if parsed_args.get("index_url"):
        pip_args += ["--index-url", parsed_args["index_url"]]

    if parsed_args.get("pip_args"):
        pip_args += shlex.split(parsed_args.get("pip_args", ""), posix=not WINDOWS)

    # make sure --editable is last because it needs to be right before
    #   package specification
    if parsed_args.get("editable"):
        pip_args += ["--editable"]
    return pip_args


def get_venv_args(parsed_args: Dict[str, str]) -> List[str]:
    venv_args: List[str] = []
    if parsed_args.get("system_site_packages"):
        venv_args += ["--system-site-packages"]
    return venv_args


def run_pipx_command(args: argparse.Namespace) -> ExitCode:  # noqa: C901
    verbose = args.verbose if "verbose" in args else False
    pip_args = get_pip_args(vars(args))
    venv_args = get_venv_args(vars(args))

    venv_container = VenvContainer(constants.PIPX_LOCAL_VENVS)

    if "package" in args:
        package = args.package
        if urllib.parse.urlparse(package).scheme:
            raise PipxError("Package cannot be a url")

        if "spec" in args and args.spec is not None:
            if urllib.parse.urlparse(args.spec).scheme:
                if "#egg=" not in args.spec:
                    args.spec = args.spec + f"#egg={package}"

        venv_dir = venv_container.get_venv_dir(package)
        logger.info(f"Virtual Environment location is {venv_dir}")
    if "skip" in args:
        skip_list = [canonicalize_name(x) for x in args.skip]

    if "python" in args:
        if args.python is not None and not Path(args.python).is_file():
            py_launcher_python = find_py_launcher_python(args.python)
            if py_launcher_python:
                args.python = py_launcher_python

    if args.command == "run":
        commands.run(
            args.app_with_args[0],
            args.spec,
            args.path,
            args.app_with_args[1:],
            args.python,
            pip_args,
            venv_args,
            args.pypackages,
            verbose,
            not args.no_cache,
        )
        # We should never reach here because run() is NoReturn.
        return ExitCode(1)
    elif args.command == "install":
        return commands.install(
            None,
            None,
            args.package_spec,
            constants.LOCAL_BIN_DIR,
            constants.LOCAL_MAN_DIR,
            args.python,
            pip_args,
            venv_args,
            verbose,
            force=args.force,
            reinstall=False,
            include_dependencies=args.include_deps,
            preinstall_packages=args.preinstall,
            suffix=args.suffix,
        )
    elif args.command == "inject":
        return commands.inject(
            venv_dir,
            None,
            args.dependencies,
            pip_args,
            verbose=verbose,
            include_apps=args.include_apps,
            include_dependencies=args.include_deps,
            force=args.force,
            suffix=args.with_suffix,
        )
    elif args.command == "uninject":
        return commands.uninject(
            venv_dir,
            args.dependencies,
            local_bin_dir=constants.LOCAL_BIN_DIR,
            local_man_dir=constants.LOCAL_MAN_DIR,
            leave_deps=args.leave_deps,
            verbose=verbose,
        )
    elif args.command == "upgrade":
        return commands.upgrade(
            venv_dir,
            pip_args,
            verbose,
            include_injected=args.include_injected,
            force=args.force,
        )
    elif args.command == "upgrade-all":
        return commands.upgrade_all(
            venv_container,
            verbose,
            include_injected=args.include_injected,
            skip=skip_list,
            force=args.force,
        )
    elif args.command == "list":
        return commands.list_packages(venv_container, args.include_injected, args.json, args.short)
    elif args.command == "uninstall":
        return commands.uninstall(venv_dir, constants.LOCAL_BIN_DIR, constants.LOCAL_MAN_DIR, verbose)
    elif args.command == "uninstall-all":
        return commands.uninstall_all(venv_container, constants.LOCAL_BIN_DIR, constants.LOCAL_MAN_DIR, verbose)
    elif args.command == "reinstall":
        return commands.reinstall(
            venv_dir=venv_dir,
            local_bin_dir=constants.LOCAL_BIN_DIR,
            local_man_dir=constants.LOCAL_MAN_DIR,
            python=args.python,
            verbose=verbose,
        )
    elif args.command == "reinstall-all":
        return commands.reinstall_all(
            venv_container,
            constants.LOCAL_BIN_DIR,
            constants.LOCAL_MAN_DIR,
            args.python,
            verbose,
            skip=skip_list,
        )
    elif args.command == "runpip":
        if not venv_dir:
            raise PipxError("Developer error: venv_dir is not defined.")
        return commands.run_pip(package, venv_dir, args.pipargs, args.verbose)
    elif args.command == "ensurepath":
        try:
            return commands.ensure_pipx_paths(force=args.force)
        except Exception as e:
            logger.debug("Uncaught Exception:", exc_info=True)
            raise PipxError(str(e), wrap_message=False)
    elif args.command == "completions":
        print(constants.completion_instructions)
        return ExitCode(0)
    elif args.command == "environment":
        return commands.environment(value=args.value)
    else:
        raise PipxError(f"Unknown command {args.command}")


def add_pip_venv_args(parser: argparse.ArgumentParser) -> None:
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


def add_include_dependencies(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--include-deps", help="Include apps of dependent packages", action="store_true")


def _add_install(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser(
        "install",
        help="Install a package",
        formatter_class=LineWrapRawTextHelpFormatter,
        description=INSTALL_DESCRIPTION,
        parents=[shared_parser],
    )
    p.add_argument("package_spec", help="package name(s) or pip installation spec(s)", nargs="*")
    add_include_dependencies(p)
    p.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Modify existing virtual environment and files in PIPX_BIN_DIR and PIPX_MAN_DIR",
    )
    p.add_argument(
        "--suffix",
        default="",
        help=(
            "Optional suffix for virtual environment and executable names. "
            "NOTE: The suffix feature is experimental and subject to change."
        ),
    )
    p.add_argument(
        "--python",
        # Don't pass a default Python here so we know whether --python flag was passed
        help=(
            "Python to install with. Possible values can be the executable name (python3.11), "
            "the version to pass to py launcher (3.11), or the full path to the executable."
            f"Requires Python {MINIMUM_PYTHON_VERSION} or above."
        ),
    )
    p.add_argument(
        "--preinstall",
        action="append",
        help=("Optional packages to be installed into the Virtual Environment before " "installing the main package."),
    )
    add_pip_venv_args(p)


def _add_inject(subparsers, venv_completer: VenvCompleter, shared_parser: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser(
        "inject",
        help="Install packages into an existing Virtual Environment",
        description="Installs packages to an existing pipx-managed virtual environment.",
        parents=[shared_parser],
    )
    p.add_argument(
        "package",
        help="Name of the existing pipx-managed Virtual Environment to inject into",
    ).completer = venv_completer
    p.add_argument(
        "dependencies",
        nargs="+",
        help="the packages to inject into the Virtual Environment--either package name or pip package spec",
    )
    p.add_argument(
        "--include-apps",
        action="store_true",
        help="Add apps from the injected packages onto your PATH and expose their manual pages",
    )
    p.add_argument(
        "--include-deps",
        help="Include apps of dependent packages. Implies --include-apps",
        action="store_true",
    )
    add_pip_venv_args(p)
    p.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Modify existing virtual environment and files in PIPX_BIN_DIR and PIPX_MAN_DIR",
    )
    p.add_argument(
        "--with-suffix",
        action="store_true",
        help="Add the suffix (if given) of the Virtual Environment to the packages to inject",
    )


def _add_uninject(subparsers, venv_completer: VenvCompleter, shared_parser: argparse.ArgumentParser):
    p = subparsers.add_parser(
        "uninject",
        help="Uninstall injected packages from an existing Virtual Environment",
        description="Uninstalls injected packages from an existing pipx-managed virtual environment.",
        parents=[shared_parser],
    )
    p.add_argument(
        "package",
        help="Name of the existing pipx-managed Virtual Environment to inject into",
    ).completer = venv_completer
    p.add_argument(
        "dependencies",
        nargs="+",
        help="the package names to uninject from the Virtual Environment",
    )
    p.add_argument(
        "--leave-deps",
        action="store_true",
        help="Only uninstall the main injected package but leave its dependencies installed.",
    )


def _add_upgrade(subparsers, venv_completer: VenvCompleter, shared_parser: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser(
        "upgrade",
        help="Upgrade a package",
        description="Upgrade a package in a pipx-managed Virtual Environment by running 'pip install --upgrade PACKAGE'",
        parents=[shared_parser],
    )
    p.add_argument("package").completer = venv_completer
    p.add_argument(
        "--include-injected",
        action="store_true",
        help="Also upgrade packages injected into the main app's environment",
    )
    p.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Modify existing virtual environment and files in PIPX_BIN_DIR and PIPX_MAN_DIR",
    )
    add_pip_venv_args(p)


def _add_upgrade_all(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser(
        "upgrade-all",
        help="Upgrade all packages. Runs `pip install -U <pkgname>` for each package.",
        description="Upgrades all packages within their virtual environments by running 'pip install --upgrade PACKAGE'",
        parents=[shared_parser],
    )
    p.add_argument(
        "--include-injected",
        action="store_true",
        help="Also upgrade packages injected into the main app's environment",
    )
    p.add_argument("--skip", nargs="+", default=[], help="skip these packages")
    p.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Modify existing virtual environment and files in PIPX_BIN_DIR and PIPX_MAN_DIR",
    )


def _add_uninstall(subparsers, venv_completer: VenvCompleter, shared_parser: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser(
        "uninstall",
        help="Uninstall a package",
        description="Uninstalls a pipx-managed Virtual Environment by deleting it and any files that point to its apps.",
        parents=[shared_parser],
    )
    p.add_argument("package").completer = venv_completer


def _add_uninstall_all(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    subparsers.add_parser(
        "uninstall-all",
        help="Uninstall all packages",
        description="Uninstall all pipx-managed packages",
        parents=[shared_parser],
    )


def _add_reinstall(subparsers, venv_completer: VenvCompleter, shared_parser: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser(
        "reinstall",
        formatter_class=LineWrapRawTextHelpFormatter,
        help="Reinstall a package",
        description=textwrap.dedent(
            """
            Reinstalls a package.

            Package is uninstalled, then installed with pipx install PACKAGE
            with the same options used in the original install of PACKAGE.

            """
        ),
        parents=[shared_parser],
    )
    p.add_argument("package").completer = venv_completer
    p.add_argument(
        "--python",
        default=DEFAULT_PYTHON,
        help=(
            "Python to reinstall with. Possible values can be the executable name (python3.11), "
            "the version to pass to py launcher (3.11), or the full path to the executable."
            f"Requires Python {MINIMUM_PYTHON_VERSION} or above."
        ),
    )


def _add_reinstall_all(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser(
        "reinstall-all",
        formatter_class=LineWrapRawTextHelpFormatter,
        help="Reinstall all packages",
        description=textwrap.dedent(
            """
            Reinstalls all packages.

            Packages are uninstalled, then installed with pipx install PACKAGE
            with the same options used in the original install of PACKAGE.
            This is useful if you upgraded to a new version of Python and want
            all your packages to use the latest as well.

            """
        ),
        parents=[shared_parser],
    )
    p.add_argument(
        "--python",
        default=DEFAULT_PYTHON,
        help=(
            "Python to reinstall with. Possible values can be the executable name (python3.11), "
            "the version to pass to py launcher (3.11), or the full path to the executable."
            f"Requires Python {MINIMUM_PYTHON_VERSION} or above."
        ),
    )
    p.add_argument("--skip", nargs="+", default=[], help="skip these packages")


def _add_list(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser(
        "list",
        help="List installed packages",
        description="List packages and apps installed with pipx",
        parents=[shared_parser],
    )
    p.add_argument(
        "--include-injected",
        action="store_true",
        help="Show packages injected into the main app's environment",
    )
    g = p.add_mutually_exclusive_group()
    g.add_argument("--json", action="store_true", help="Output rich data in json format.")
    g.add_argument("--short", action="store_true", help="List packages only.")


def _add_run(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser(
        "run",
        formatter_class=LineWrapRawTextHelpFormatter,
        help=(
            "Download the latest version of a package to a temporary virtual environment, "
            "then run an app from it. Also compatible with local `__pypackages__` "
            "directory (experimental)."
        ),
        description=textwrap.dedent(
            f"""
            Download the latest version of a package to a temporary virtual environment,
            then run an app from it. The environment will be cached
            and re-used for up to {constants.TEMP_VENV_EXPIRATION_THRESHOLD_DAYS} days. This
            means subsequent calls to 'run' for the same package will be faster
            since they can re-use the cached Virtual Environment.

            In support of PEP 582 'run' will use apps found in a local __pypackages__
            directory, if present. Please note that this behavior is experimental,
            and acts as a companion tool to pythonloc. It may be modified or
            removed in the future. See https://github.com/cs01/pythonloc.
            """
        ),
        parents=[shared_parser],
    )
    p.add_argument(
        "--no-cache",
        action="store_true",
        help="Do not re-use cached virtual environment if it exists",
    )
    p.add_argument(
        "app_with_args",
        metavar="app ...",
        nargs=argparse.REMAINDER,
        help="app/package name and any arguments to be passed to it",
        default=[],
    )
    p.add_argument("--path", action="store_true", help="Interpret app name as a local path")
    p.add_argument(
        "--pypackages",
        action="store_true",
        help="Require app to be run from local __pypackages__ directory",
    )
    p.add_argument("--spec", help=SPEC_HELP)
    p.add_argument(
        "--python",
        default=DEFAULT_PYTHON,
        help=(
            "Python to run with. Possible values can be the executable name (python3.11), "
            "the version to pass to py launcher (3.11), or the full path to the executable. "
            f"Requires Python {MINIMUM_PYTHON_VERSION} or above."
        ),
    )
    add_pip_venv_args(p)
    p.set_defaults(subparser=p)

    # modify usage text to show required app argument
    p.usage = re.sub(r"^usage: ", "", p.format_usage())
    # add a double-dash to usage text to show requirement before app
    p.usage = re.sub(r"\.\.\.", "app ...", p.usage)


def _add_runpip(subparsers, venv_completer: VenvCompleter, shared_parser: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser(
        "runpip",
        help="Run pip in an existing pipx-managed Virtual Environment",
        description="Run pip in an existing pipx-managed Virtual Environment",
        parents=[shared_parser],
    )
    p.add_argument(
        "package",
        help="Name of the existing pipx-managed Virtual Environment to run pip in",
    ).completer = venv_completer
    p.add_argument(
        "pipargs",
        nargs=argparse.REMAINDER,
        default=[],
        help="Arguments to forward to pip command",
    )


def _add_ensurepath(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser(
        "ensurepath",
        help=("Ensure directories necessary for pipx operation are in your " "PATH environment variable."),
        description=(
            "Ensure directory where pipx stores apps is in your "
            "PATH environment variable. Also if pipx was installed via "
            "`pip install --user`, ensure pipx itself is in your PATH. "
            "Note that running this may modify "
            "your shell's configuration file(s) such as '~/.bashrc'."
        ),
        parents=[shared_parser],
    )
    p.add_argument(
        "--force",
        "-f",
        action="store_true",
        help=(
            "Add text to your shell's config file even if it looks like your "
            "PATH already contains paths to pipx and pipx-install apps."
        ),
    )


def _add_environment(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser(
        "environment",
        formatter_class=LineWrapRawTextHelpFormatter,
        help="Print a list of environment variables and paths used by pipx.",
        description=textwrap.dedent(
            """
            Prints the names and current values of environment variables used by pipx,
            followed by internal pipx variables which are derived from the environment
            variables and platform specific default values.

            Available variables:
            PIPX_HOME, PIPX_BIN_DIR, PIPX_MAN_DIR, PIPX_SHARED_LIBS, PIPX_LOCAL_VENVS,
            PIPX_LOG_DIR, PIPX_TRASH_DIR, PIPX_VENV_CACHEDIR, PIPX_DEFAULT_PYTHON, USE_EMOJI
            """
        ),
        parents=[shared_parser],
    )
    p.add_argument("--value", "-V", metavar="VARIABLE", help="Print the value of the variable.")


def get_command_parser() -> argparse.ArgumentParser:
    venv_container = VenvContainer(constants.PIPX_LOCAL_VENVS)

    completer_venvs = InstalledVenvsCompleter(venv_container)

    parser = argparse.ArgumentParser(
        prog=prog_name(),
        formatter_class=LineWrapRawTextHelpFormatter,
        description=PIPX_DESCRIPTION,
    )
    parser.man_short_description = PIPX_DESCRIPTION.splitlines()[1]  # type: ignore

    subparsers = parser.add_subparsers(dest="command", description="Get help for commands with pipx COMMAND --help")

    shared_parser = argparse.ArgumentParser(add_help=False)

    shared_parser.add_argument(
        "--quiet",
        "-q",
        action="count",
        default=0,
        help=(
            "Give less output. May be used multiple times corresponding to the"
            " WARNING, ERROR, and CRITICAL logging levels."
        ),
    )

    shared_parser.add_argument("--verbose", "-v", action="count", default=0, help=("Give more output."))

    _add_install(subparsers, shared_parser)
    _add_uninject(subparsers, completer_venvs.use, shared_parser)
    _add_inject(subparsers, completer_venvs.use, shared_parser)
    _add_upgrade(subparsers, completer_venvs.use, shared_parser)
    _add_upgrade_all(subparsers, shared_parser)
    _add_uninstall(subparsers, completer_venvs.use, shared_parser)
    _add_uninstall_all(subparsers, shared_parser)
    _add_reinstall(subparsers, completer_venvs.use, shared_parser)
    _add_reinstall_all(subparsers, shared_parser)
    _add_list(subparsers, shared_parser)
    _add_run(subparsers, shared_parser)
    _add_runpip(subparsers, completer_venvs.use, shared_parser)
    _add_ensurepath(subparsers, shared_parser)
    _add_environment(subparsers, shared_parser)

    parser.add_argument("--version", action="store_true", help="Print version and exit")
    subparsers.add_parser(
        "completions",
        help="Print instructions on enabling shell completions for pipx",
        description="Print instructions on enabling shell completions for pipx",
        parents=[shared_parser],
    )
    return parser


def delete_oldest_logs(file_list: List[Path], keep_number: int) -> None:
    file_list = sorted(file_list)
    if len(file_list) > keep_number:
        for existing_file in file_list[:-keep_number]:
            try:
                existing_file.unlink()
            except FileNotFoundError:
                pass


def _setup_log_file(pipx_log_dir: Optional[Path] = None) -> Path:
    max_logs = 10
    pipx_log_dir = pipx_log_dir or constants.PIPX_LOG_DIR
    # don't use utils.mkdir, to prevent emission of log message
    pipx_log_dir.mkdir(parents=True, exist_ok=True)

    delete_oldest_logs(list(pipx_log_dir.glob("cmd_*[0-9].log")), max_logs)
    delete_oldest_logs(list(pipx_log_dir.glob("cmd_*_pip_errors.log")), max_logs)

    datetime_str = time.strftime("%Y-%m-%d_%H.%M.%S")
    log_file = pipx_log_dir / f"cmd_{datetime_str}.log"
    counter = 1
    while log_file.exists() and counter < 10:
        log_file = pipx_log_dir / f"cmd_{datetime_str}_{counter}.log"
        counter += 1

    log_file.touch()

    return log_file


def setup_log_file() -> Path:
    try:
        return _setup_log_file()
    except PermissionError:
        return _setup_log_file(platformdirs.user_log_path("pipx"))


def setup_logging(verbose: bool) -> None:
    pipx_str = bold(green("pipx >")) if sys.stdout.isatty() else "pipx >"
    pipx.constants.pipx_log_file = setup_log_file()

    # Determine logging level
    level_number = max(0, 2 - verbose) * 10

    level = logging.getLevelName(level_number)

    # "incremental" is False so previous pytest tests don't accumulate handlers
    logging_config = {
        "version": 1,
        "formatters": {
            "stream_nonverbose": {
                "class": "logging.Formatter",
                "format": "{message}",
                "style": "{",
            },
            "stream_verbose": {
                "class": "logging.Formatter",
                "format": pipx_str + "({funcName}:{lineno}): {message}",
                "style": "{",
            },
            "file": {
                "class": "logging.Formatter",
                "format": "{relativeCreated: >8.1f}ms ({funcName}:{lineno}): {message}",
                "style": "{",
            },
        },
        "handlers": {
            "stream": {
                "class": "logging.StreamHandler",
                "formatter": "stream_verbose" if verbose else "stream_nonverbose",
                "level": level,
            },
            "file": {
                "class": "logging.FileHandler",
                "formatter": "file",
                "filename": str(pipx.constants.pipx_log_file),
                "encoding": "utf-8",
                "level": "DEBUG",
            },
        },
        "loggers": {"pipx": {"handlers": ["stream", "file"], "level": "DEBUG"}},
        "incremental": False,
    }
    logging.config.dictConfig(logging_config)


def setup(args: argparse.Namespace) -> None:
    if "version" in args and args.version:
        print_version()
        sys.exit(0)

    verbose = args.verbose - args.quiet

    setup_logging(verbose)

    logger.debug(f"{time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.debug(f"{' '.join(sys.argv)}")
    logger.info(f"pipx version is {__version__}")
    logger.info(f"Default python interpreter is '{DEFAULT_PYTHON}'")

    mkdir(constants.PIPX_LOCAL_VENVS)
    mkdir(constants.LOCAL_BIN_DIR)
    mkdir(constants.LOCAL_MAN_DIR)
    mkdir(constants.PIPX_VENV_CACHEDIR)

    cachedir_tag = constants.PIPX_VENV_CACHEDIR / "CACHEDIR.TAG"
    if not cachedir_tag.exists():
        logger.debug("Adding CACHEDIR.TAG to cache directory")
        signature = (
            "Signature: 8a477f597d28d172789f06886806bc55\n"
            "# This file is a cache directory tag created by pipx.\n"
            "# For information about cache directory tags, see:\n"
            "#       https://bford.info/cachedir/\n"
        )
        with open(cachedir_tag, "w") as file:
            file.write(signature)

    rmdir(constants.PIPX_TRASH_DIR, False)

    old_pipx_venv_location = constants.PIPX_LOCAL_VENVS / "pipx-app"
    if old_pipx_venv_location.exists():
        logger.warning(
            pipx_wrap(
                f"""
                {hazard}  A virtual environment for pipx was detected at
                {str(old_pipx_venv_location)}. The 'pipx-app' package has been
                renamed back to 'pipx'
                (https://github.com/pypa/pipx/issues/82).
                """,
                subsequent_indent=" " * 4,
            )
        )


def check_args(parsed_pipx_args: argparse.Namespace) -> None:
    if parsed_pipx_args.command == "run":
        # we manually discard a first -- because using nargs=argparse.REMAINDER
        #   will not do it automatically
        if parsed_pipx_args.app_with_args and parsed_pipx_args.app_with_args[0] == "--":
            parsed_pipx_args.app_with_args.pop(0)
        # since we would like app to be required but not in a separate argparse
        #   add_argument, we implement our own missing required arg error
        if not parsed_pipx_args.app_with_args:
            parsed_pipx_args.subparser.error("the following arguments are required: app")


def cli() -> ExitCode:
    """Entry point from command line"""
    try:
        hide_cursor()
        parser = get_command_parser()
        argcomplete.autocomplete(parser)
        parsed_pipx_args = parser.parse_args()
        setup(parsed_pipx_args)
        check_args(parsed_pipx_args)
        if not parsed_pipx_args.command:
            parser.print_help()
            return ExitCode(1)
        return run_pipx_command(parsed_pipx_args)
    except PipxError as e:
        print(str(e), file=sys.stderr)
        logger.debug(f"PipxError: {e}", exc_info=True)
        return ExitCode(1)
    except KeyboardInterrupt:
        return ExitCode(1)
    except Exception:
        logger.debug("Uncaught Exception:", exc_info=True)
        raise
    finally:
        logger.debug("pipx finished.")
        show_cursor()


if __name__ == "__main__":
    sys.exit(cli())
