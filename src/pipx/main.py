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
from typing import Any, Callable, Dict, List

import argcomplete  # type: ignore
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

import pipx.constants
from pipx import commands, constants
from pipx.animate import hide_cursor, show_cursor
from pipx.colors import bold, green
from pipx.constants import ExitCode
from pipx.emojis import hazard
from pipx.interpreter import DEFAULT_PYTHON
from pipx.util import PipxError, mkdir, pipx_wrap, rmdir
from pipx.venv import VenvContainer
from pipx.version import __version__

logger = logging.getLogger(__name__)

VenvCompleter = Callable[[str], List[str]]


def print_version() -> None:
    print(__version__)


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

    """
)
PIPX_DESCRIPTION += pipx_wrap(
    """
    optional environment variables:
      PIPX_HOME             Overrides default pipx location. Virtual Environments will be installed to $PIPX_HOME/venvs.
      PIPX_BIN_DIR          Overrides location of app installations. Apps are symlinked or copied here.
      USE_EMOJI             Overrides emoji behavior. Default value varies based on platform.
      PIPX_DEFAULT_PYTHON   Overrides default python used for commands.
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
    accessible on your $PATH.

    The result: apps you can run from anywhere, located in packages
    you can cleanly upgrade or uninstall. Guaranteed to not have
    dependency version conflicts or interfere with your OS's python
    packages. 'sudo' is not required to do this.

    pipx install PACKAGE_NAME
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
        return [
            f"{prefix}{x[len(prefix):]}"
            for x in self.packages
            if x.startswith(canonicalize_name(prefix))
        ]


def get_pip_args(parsed_args: Dict[str, str]) -> List[str]:
    pip_args: List[str] = []
    if parsed_args.get("index_url"):
        pip_args += ["--index-url", parsed_args["index_url"]]

    if parsed_args.get("pip_args"):
        pip_args += shlex.split(parsed_args.get("pip_args", ""))

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

    if args.command == "run":
        package_or_url = (
            args.spec
            if ("spec" in args and args.spec is not None)
            else args.app_with_args[0]
        )
        # For any package, we need to just use the name
        try:
            package_name = Requirement(args.app_with_args[0]).name
        except InvalidRequirement:
            # Raw URLs to scripts are supported, too, so continue if
            # we can't parse this as a package
            package_name = args.app_with_args[0]

        use_cache = not args.no_cache
        commands.run(
            package_name,
            package_or_url,
            args.app_with_args[1:],
            args.python,
            pip_args,
            venv_args,
            args.pypackages,
            verbose,
            use_cache,
        )
        # We should never reach here because run() is NoReturn.
        return ExitCode(1)
    elif args.command == "install":
        return commands.install(
            None,
            None,
            args.package_spec,
            constants.LOCAL_BIN_DIR,
            args.python,
            pip_args,
            venv_args,
            verbose,
            force=args.force,
            include_dependencies=args.include_deps,
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
        return commands.list_packages(venv_container, args.include_injected, args.json)
    elif args.command == "uninstall":
        return commands.uninstall(venv_dir, constants.LOCAL_BIN_DIR, verbose)
    elif args.command == "uninstall-all":
        return commands.uninstall_all(venv_container, constants.LOCAL_BIN_DIR, verbose)
    elif args.command == "reinstall":
        return commands.reinstall(
            venv_dir=venv_dir,
            local_bin_dir=constants.LOCAL_BIN_DIR,
            python=args.python,
            verbose=verbose,
        )
    elif args.command == "reinstall-all":
        return commands.reinstall_all(
            venv_container,
            constants.LOCAL_BIN_DIR,
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
    parser.add_argument(
        "--include-deps", help="Include apps of dependent packages", action="store_true"
    )


def _add_install(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "install",
        help="Install a package",
        formatter_class=LineWrapRawTextHelpFormatter,
        description=INSTALL_DESCRIPTION,
    )
    p.add_argument("package_spec", help="package name or pip installation spec")
    add_include_dependencies(p)
    p.add_argument("--verbose", action="store_true")
    p.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Modify existing virtual environment and files in PIPX_BIN_DIR",
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
        default=DEFAULT_PYTHON,
        help=(
            "The Python executable used to create the Virtual Environment and run the "
            "associated app/apps. Must be v3.6+."
        ),
    )
    add_pip_venv_args(p)


def _add_inject(subparsers, venv_completer: VenvCompleter) -> None:
    p = subparsers.add_parser(
        "inject",
        help="Install packages into an existing Virtual Environment",
        description="Installs packages to an existing pipx-managed virtual environment.",
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
        help="Add apps from the injected packages onto your PATH",
    )
    add_include_dependencies(p)
    add_pip_venv_args(p)
    p.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Modify existing virtual environment and files in PIPX_BIN_DIR",
    )
    p.add_argument("--verbose", action="store_true")


def _add_upgrade(subparsers, venv_completer: VenvCompleter) -> None:
    p = subparsers.add_parser(
        "upgrade",
        help="Upgrade a package",
        description="Upgrade a package in a pipx-managed Virtual Environment by running 'pip install --upgrade PACKAGE'",
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
        help="Modify existing virtual environment and files in PIPX_BIN_DIR",
    )
    add_pip_venv_args(p)
    p.add_argument("--verbose", action="store_true")


def _add_upgrade_all(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "upgrade-all",
        help="Upgrade all packages. Runs `pip install -U <pkgname>` for each package.",
        description="Upgrades all packages within their virtual environments by running 'pip install --upgrade PACKAGE'",
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
        help="Modify existing virtual environment and files in PIPX_BIN_DIR",
    )
    p.add_argument("--verbose", action="store_true")


def _add_uninstall(subparsers, venv_completer: VenvCompleter) -> None:
    p = subparsers.add_parser(
        "uninstall",
        help="Uninstall a package",
        description="Uninstalls a pipx-managed Virtual Environment by deleting it and any files that point to its apps.",
    )
    p.add_argument("package").completer = venv_completer
    p.add_argument("--verbose", action="store_true")


def _add_uninstall_all(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "uninstall-all",
        help="Uninstall all packages",
        description="Uninstall all pipx-managed packages",
    )
    p.add_argument("--verbose", action="store_true")


def _add_reinstall(subparsers, venv_completer: VenvCompleter) -> None:
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
    )
    p.add_argument("package").completer = venv_completer
    p.add_argument(
        "--python",
        default=DEFAULT_PYTHON,
        help=(
            "The Python executable used to recreate the Virtual Environment "
            "and run the associated app/apps. Must be v3.6+."
        ),
    )
    p.add_argument("--verbose", action="store_true")


def _add_reinstall_all(subparsers: argparse._SubParsersAction) -> None:
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
    )
    p.add_argument(
        "--python",
        default=DEFAULT_PYTHON,
        help=(
            "The Python executable used to recreate the Virtual Environment "
            "and run the associated app/apps. Must be v3.6+."
        ),
    )
    p.add_argument("--skip", nargs="+", default=[], help="skip these packages")
    p.add_argument("--verbose", action="store_true")


def _add_list(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "list",
        help="List installed packages",
        description="List packages and apps installed with pipx",
    )
    p.add_argument(
        "--include-injected",
        action="store_true",
        help="Show packages injected into the main app's environment",
    )
    p.add_argument(
        "--json", action="store_true", help="Output rich data in json format."
    )
    p.add_argument("--verbose", action="store_true")


def _add_run(subparsers: argparse._SubParsersAction) -> None:
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
    p.add_argument(
        "--pypackages",
        action="store_true",
        help="Require app to be run from local __pypackages__ directory",
    )
    p.add_argument("--spec", help=SPEC_HELP)
    p.add_argument("--verbose", action="store_true")
    p.add_argument(
        "--python",
        default=DEFAULT_PYTHON,
        help="The Python version to run package's CLI app with. Must be v3.6+.",
    )
    add_pip_venv_args(p)
    p.set_defaults(subparser=p)

    # modify usage text to show required app argument
    p.usage = re.sub(r"^usage: ", "", p.format_usage())
    # add a double-dash to usage text to show requirement before app
    p.usage = re.sub(r"\.\.\.", "app ...", p.usage)


def _add_runpip(subparsers, venv_completer: VenvCompleter) -> None:
    p = subparsers.add_parser(
        "runpip",
        help="Run pip in an existing pipx-managed Virtual Environment",
        description="Run pip in an existing pipx-managed Virtual Environment",
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
    p.add_argument("--verbose", action="store_true")


def _add_ensurepath(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "ensurepath",
        help=(
            "Ensure directories necessary for pipx operation are in your "
            "PATH environment variable."
        ),
        description=(
            "Ensure directory where pipx stores apps is in your "
            "PATH environment variable. Also if pipx was installed via "
            "`pip install --user`, ensure pipx itself is in your PATH. "
            "Note that running this may modify "
            "your shell's configuration file(s) such as '~/.bashrc'."
        ),
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


def get_command_parser() -> argparse.ArgumentParser:
    venv_container = VenvContainer(constants.PIPX_LOCAL_VENVS)

    completer_venvs = InstalledVenvsCompleter(venv_container)

    parser = argparse.ArgumentParser(
        prog="pipx",
        formatter_class=LineWrapRawTextHelpFormatter,
        description=PIPX_DESCRIPTION,
    )
    parser.man_short_description = PIPX_DESCRIPTION.splitlines()[1]  # type: ignore

    subparsers = parser.add_subparsers(
        dest="command", description="Get help for commands with pipx COMMAND --help"
    )

    _add_install(subparsers)
    _add_inject(subparsers, completer_venvs.use)
    _add_upgrade(subparsers, completer_venvs.use)
    _add_upgrade_all(subparsers)
    _add_uninstall(subparsers, completer_venvs.use)
    _add_uninstall_all(subparsers)
    _add_reinstall(subparsers, completer_venvs.use)
    _add_reinstall_all(subparsers)
    _add_list(subparsers)
    _add_run(subparsers)
    _add_runpip(subparsers, completer_venvs.use)
    _add_ensurepath(subparsers)

    parser.add_argument("--version", action="store_true", help="Print version and exit")
    subparsers.add_parser(
        "completions",
        help="Print instructions on enabling shell completions for pipx",
        description="Print instructions on enabling shell completions for pipx",
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


def setup_log_file() -> Path:
    max_logs = 10
    # don't use utils.mkdir, to prevent emission of log message
    constants.PIPX_LOG_DIR.mkdir(parents=True, exist_ok=True)

    delete_oldest_logs(list(constants.PIPX_LOG_DIR.glob("cmd_*[0-9].log")), max_logs)
    delete_oldest_logs(
        list(constants.PIPX_LOG_DIR.glob("cmd_*_pip_errors.log")), max_logs
    )

    datetime_str = time.strftime("%Y-%m-%d_%H.%M.%S")
    log_file = constants.PIPX_LOG_DIR / f"cmd_{datetime_str}.log"
    counter = 1
    while log_file.exists() and counter < 10:
        log_file = constants.PIPX_LOG_DIR / f"cmd_{datetime_str}_{counter}.log"
        counter += 1

    return log_file


def setup_logging(verbose: bool) -> None:
    pipx_str = bold(green("pipx >")) if sys.stdout.isatty() else "pipx >"
    pipx.constants.pipx_log_file = setup_log_file()

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
                "level": "INFO" if verbose else "WARNING",
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

    setup_logging("verbose" in args and args.verbose)

    logger.debug(f"{time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.debug(f"{' '.join(sys.argv)}")
    logger.info(f"pipx version is {__version__}")
    logger.info(f"Default python interpreter is {repr(DEFAULT_PYTHON)}")

    mkdir(constants.PIPX_LOCAL_VENVS)
    mkdir(constants.LOCAL_BIN_DIR)
    mkdir(constants.PIPX_VENV_CACHEDIR)

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
            parsed_pipx_args.subparser.error(
                "the following arguments are required: app"
            )


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
