# PYTHON_ARGCOMPLETE_OK

"""The command line interface to pipx"""

from __future__ import annotations

__lazy_modules__ = [
    "argcomplete",
    "contextlib",
    "fcntl",
    "packaging.utils",
    "pathlib",
    "pipx",
    "pipx.backends._base",
    "pipx.backends.registry",
    "pipx.commands.environment",
    "pipx.commands.transaction",
    "pipx.fanout",
    "pipx.interpreter",
    "pipx.options",
    "pipx.package_specifier",
    "pipx.redact",
    "pipx.result",
    "pipx.shared_libs",
    "pipx.subprocess_runner",
    "pipx.util",
    "pipx.venv",
    "pipx.version",
    "pipx.wrap",
    "platformdirs",
    "re",
    "shlex",
    "textwrap",
    "urllib.parse",
]

import argparse
import contextlib
import logging
import os
import re
import shlex
import sys
import textwrap
import time
import typing
import urllib.parse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, NoReturn, TextIO, cast

import argcomplete
import platformdirs
from packaging.utils import canonicalize_name

from pipx import constants, paths
from pipx.animate import hide_cursor, show_cursor
from pipx.backends._base import KNOWN_BACKENDS, UV
from pipx.backends.registry import env_default_backend, get_backend, resolve_backend_name
from pipx.colors import BOLD, GREEN
from pipx.commands.environment import ENVIRONMENT_VALUE_CHOICES, ENVIRONMENT_VARIABLES
from pipx.commands.transaction import empty_trash
from pipx.constants import (
    EXIT_CODE_OK,
    EXIT_CODE_SPECIFIED_PYTHON_EXECUTABLE_NOT_FOUND,
    MINIMUM_PYTHON_VERSION,
    WINDOWS,
    ExitCode,
    FetchPythonOptions,
)
from pipx.emojis import HAZARD
from pipx.fanout import stopping_children_on_signals
from pipx.interpreter import (
    InterpreterResolutionError,
    find_python_interpreter,
    get_default_python,
    get_default_python_spec,
)
from pipx.options import (
    BackendOptions,
    CooldownOptions,
    ExposureOptions,
    InjectOptions,
    InstallOptions,
    ListOptions,
    ReinstallOptions,
    RunOptions,
    SyncOptions,
    UninjectOptions,
    UpgradeOptions,
)
from pipx.package_specifier import valid_pypi_name
from pipx.redact import redact_url_credentials
from pipx.result import OperationError, OperationResult, OutputFormat, error_envelope, render_result
from pipx.shared_libs import shared_pip_cooldown, skip_shared_libs_maintenance
from pipx.subprocess_runner import stream_subprocess_stdout_to_stderr
from pipx.util import PipxError, mkdir, open_owner_only, reject_empty_index
from pipx.venv import VenvContainer
from pipx.version import version as __version__
from pipx.wrap import pipx_wrap

if not WINDOWS:
    import fcntl

if TYPE_CHECKING:
    from io import TextIOWrapper

    from pipx.commands.cache import CacheData
    from pipx.commands.expose import ExposureData
    from pipx.commands.health import HealthData, RepairData
    from pipx.commands.inject import InjectionData
    from pipx.commands.install import InstallData
    from pipx.commands.interpreter import InterpreterData
    from pipx.commands.manifest import ManifestData
    from pipx.commands.outdated import OutdatedData
    from pipx.commands.pin import PinData
    from pipx.commands.reinstall import ReinstallData
    from pipx.commands.reset import ResetData
    from pipx.commands.uninstall import UninstallData
    from pipx.commands.upgrade import SharedData, UpgradeData

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

_VenvCompleter = Callable[[str], list[str]]

_FORCE_INSTALL_HELP: Final[str] = (
    "Modify existing virtual environment and files in PIPX_BIN_DIR and PIPX_MAN_DIR; --python does not change an "
    "existing environment's Python, use `pipx reinstall --python` for that"
)

_IGNORED_ON_EXISTING_VENV: Final[str] = (
    " Ignored, since the existing environment keeps the venv options it was installed with; accepted for compatibility."
)


def cli() -> ExitCode:
    try:
        with stopping_children_on_signals() as signalled:
            hide_cursor()
            # a command that finished its work after an interrupt still reports being interrupted
            return ExitCode(_dispatch(sys.argv[1:]) or int(signalled.is_set()))
    except PipxError as error:
        print(str(error), file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output
        _LOGGER.debug("PipxError: %s", error, exc_info=True)
        return ExitCode(1)
    except KeyboardInterrupt:
        return ExitCode(1)
    except Exception:  # record any crash's traceback in the log file before Python prints it
        _LOGGER.debug("Uncaught Exception:", exc_info=True)
        raise
    finally:
        _LOGGER.debug("pipx finished.")
        show_cursor()


def _dispatch(argv: list[str]) -> ExitCode:
    parser: Final[argparse.ArgumentParser] = get_command_parser()
    argcomplete.autocomplete(parser, always_complete_options=False)
    parsed_pipx_args: Final[argparse.Namespace] = parse_pipx_args(parser, argv)
    try:
        _setup(parsed_pipx_args)
        check_args(parsed_pipx_args)
        if not parsed_pipx_args.command:
            parser.print_help()
            return ExitCode(1)
        return _run_pipx_command(parsed_pipx_args)
    except PipxError as error:
        # with JSON output selected, a failure still has to print the result envelope
        if _output_format(parsed_pipx_args) is not OutputFormat.JSON:
            raise
        print(  # ruff:ignore[print]  # user-facing CLI output
            error_envelope(
                _command_tokens(parsed_pipx_args), OperationError(code="pipx_error", message=str(error)), ExitCode(1)
            )
        )
        return ExitCode(1)


def build_parser() -> argparse.ArgumentParser:
    # sphinx-argparse-cli renders the CLI reference from this parser, so the docs cannot drift from the arguments. The
    # program is named here rather than taken from the docs builder's argv[0]: each subcommand parser copies prog when
    # it is created, and the directive's :prog: option cannot rewrite it afterwards.
    return get_command_parser(prog="pipx")


def get_command_parser(*, prog: str | None = None) -> argparse.ArgumentParser:
    completer_venvs: Final[InstalledVenvsCompleter] = InstalledVenvsCompleter(VenvContainer(paths.CTX.venvs))
    shared_parser: Final[argparse.ArgumentParser] = argparse.ArgumentParser(add_help=False)

    shared_parser.add_argument(
        "--quiet",
        "-q",
        action="count",
        default=0,
        help=(
            "Give less output. May be used multiple times corresponding to the"
            " ERROR and CRITICAL logging levels. The count maxes out at 2."
        ),
    )

    shared_parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help=(
            "Give more output. May be used multiple times corresponding to the"
            " INFO, DEBUG and NOTSET logging levels. The count maxes out at 3."
        ),
    )

    shared_parser.add_argument(
        "--skip-maintenance",
        action="store_true",
        help="Do not upgrade shared libraries; use bundled pip when creating them.",
    )

    if not constants.WINDOWS:
        shared_parser.add_argument(
            "--global",
            action="store_true",
            dest="is_global",
            help="Perform action globally for all users.",
        )

    parser: Final[argparse.ArgumentParser] = argparse.ArgumentParser(
        prog=prog or prog_name(),
        formatter_class=_LineWrapRawTextHelpFormatter,
        description=textwrap.dedent(
            f"""
            Install and execute apps from Python packages.

            Binaries can either be installed globally into isolated Virtual Environments
            or run directly in a temporary Virtual Environment.

            Virtual Environment location is {paths.CTX.venvs!s}.
            Symlinks to apps are placed in {paths.CTX.bin_dir!s}.
            Symlinks to manual pages are placed in {paths.CTX.man_dir!s}.

            """
        )
        + pipx_wrap(
            "optional environment variables:\n"
            "  PIPX_HOME              Overrides default pipx location. "
            "Virtual Environments will be installed to $PIPX_HOME/venvs.\n"
            "  PIPX_GLOBAL_HOME       Used instead of PIPX_HOME when the `--global` option is given.\n"
            "  PIPX_BIN_DIR           Overrides location of app installations. Apps are symlinked or copied here.\n"
            "  PIPX_GLOBAL_BIN_DIR    Used instead of PIPX_BIN_DIR when the `--global` option is given.\n"
            "  PIPX_MAN_DIR           Overrides location of manual pages installations. "
            "Manual pages are symlinked or copied here.\n"
            "  PIPX_GLOBAL_MAN_DIR    Used instead of PIPX_MAN_DIR when the `--global` option is given.\n"
            "  PIPX_COMPLETION_DIR    Overrides location of shell completion installations. "
            "Completion scripts are symlinked or copied here.\n"
            "  PIPX_GLOBAL_COMPLETION_DIR\n"
            "                        Used instead of PIPX_COMPLETION_DIR when the `--global` option is given.\n"
            "  PIPX_DEFAULT_PYTHON    Overrides default python used for commands.\n"
            "  PIPX_DEFAULT_BACKEND   Overrides which backend (`pip` or `uv`) is used for new venvs.\n"
            "  PIPX_COOLDOWN          Default `--cooldown` in days for the commands that accept it.\n"
            "  PIPX_DISABLE_SHARED_LIBS_AUTO_UPGRADE\n"
            "                        Skips automatic shared library upgrades.\n"
            "  PIPX_USE_EMOJI         Overrides emoji behavior. Default value varies based on platform.",
            subsequent_indent=" " * 24,  # match the indent of argparse options
            keep_newlines=True,
        ),
    )

    subparsers: Final[argparse._SubParsersAction] = parser.add_subparsers(
        dest="command", description="Get help for commands with pipx COMMAND --help"
    )

    _add_install(subparsers, shared_parser)
    _add_install_all(subparsers, shared_parser)
    _add_uninject(subparsers, completer_venvs.use, shared_parser)
    _add_inject(subparsers, completer_venvs.use, shared_parser)
    _add_expose(subparsers, completer_venvs.use, shared_parser)
    _add_unexpose(subparsers, completer_venvs.use, shared_parser)
    _add_pin(subparsers, shared_parser)
    _add_unpin(subparsers, shared_parser)
    _add_upgrade(subparsers, completer_venvs.use, shared_parser)
    _add_upgrade_all(subparsers, shared_parser)
    _add_upgrade_shared(subparsers, shared_parser)
    _add_uninstall(subparsers, completer_venvs.use, shared_parser)
    _add_uninstall_all(subparsers, shared_parser)
    _add_reset(subparsers, shared_parser)
    _add_reinstall(subparsers, completer_venvs.use, shared_parser)
    _add_reinstall_all(subparsers, shared_parser)
    _add_health(subparsers, completer_venvs.use, shared_parser)
    _add_repair(subparsers, completer_venvs.use, shared_parser)
    _add_list(subparsers, completer_venvs.use, shared_parser)
    _add_interpreter(subparsers, shared_parser)
    _add_cache(subparsers, shared_parser)
    _add_manifest(subparsers, shared_parser)
    _add_run(subparsers, shared_parser)
    _add_execute(subparsers, completer_venvs.use, shared_parser)
    _add_runpip(subparsers, completer_venvs.use, shared_parser)
    _add_ensurepath(subparsers, shared_parser)
    _add_environment(subparsers, shared_parser)

    parser.add_argument("--version", action="store_true", help="Print version and exit")
    completions_parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "completions",
        help="Print instructions on enabling shell completions for pipx",
        description="Print instructions on enabling shell completions for pipx",
        parents=[shared_parser],
    )
    completions_parser.set_defaults(func=_cmd_completions)
    help_parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "help",
        help="Show help for pipx or a command",
        description="Show help for pipx or a command",
        parents=[shared_parser],
    )
    help_parser.set_defaults(func=_make_print_help(parser))
    return parser


class InstalledVenvsCompleter:
    def __init__(self, venv_container: VenvContainer) -> None:
        self._venv_container: Final[VenvContainer] = venv_container
        self._packages: list[str] | None = None

    def use(self, prefix: str, **_kwargs: argparse.Action | argparse.ArgumentParser | argparse.Namespace) -> list[str]:
        if self._packages is None:
            self._packages = [path.name for path in sorted(self._venv_container.iter_venv_dirs())]
        canonical_prefix: Final[str] = canonicalize_name(prefix)
        return [
            f"{prefix}{name[len(canonical_prefix) :]}" for name in self._packages if name.startswith(canonical_prefix)
        ]


def prog_name() -> str:
    with contextlib.suppress(IndexError):
        prog: Final[str] = Path(sys.argv[0]).name
        return f"{sys.executable} -m pipx" if prog == "__main__.py" else prog
    return "pipx"


class _LineWrapRawTextHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def _split_lines(self, text: str, width: int) -> list[str]:
        return textwrap.wrap(self._whitespace_matcher.sub(" ", text).strip(), width)


def _add_install(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "install",
        help="Install a package",
        formatter_class=_LineWrapRawTextHelpFormatter,
        description=textwrap.dedent(
            f"""
            The install command is the preferred way to globally install apps
            from Python packages and PEP 723 scripts. It creates an isolated virtual
            environment for the source, then ensures its apps are
            accessible on your $PATH. The package's manual pages installed in
            share/man/man[1-9] can be viewed with man on an operating system where
            it is available and the path in the environment variable `PIPX_MAN_DIR`
            (default: {paths.DEFAULT_PIPX_MAN_DIR}) is in the man search path
            ($MANPATH).

            You get apps you can run from anywhere, in packages you can
            cleanly upgrade or uninstall. Each package gets its own virtual
            environment, so its dependencies cannot conflict with those of
            other packages or interfere with your OS's python packages. You
            do not need 'sudo' for this.

            pipx install PACKAGE_SPEC ...
            pipx install --python PYTHON PACKAGE_SPEC
            pipx install VCS_URL
            pipx install ./LOCAL_PATH
            pipx install ./SCRIPT.py
            pipx install ZIP_FILE
            pipx install TAR_GZ_FILE

            Package specs are passed to the selected backend. PEP 723 scripts are
            installed with their declared dependencies.

            Virtual Environments will be installed to `$PIPX_HOME/venvs`.
            The default pipx home location is {paths.DEFAULT_PIPX_HOME} and can
            be overridden by setting the environment variable `PIPX_HOME`.
            If the `--global` option is used, the default pipx home location
            instead is {paths.DEFAULT_PIPX_GLOBAL_HOME} and can be overridden
            by setting the environment variable `PIPX_GLOBAL_HOME`.

            The default app location is {paths.DEFAULT_PIPX_BIN_DIR} and can be
            overridden by setting the environment variable `PIPX_BIN_DIR`.
            If the `--global` option is used, the default app location instead
            is {paths.DEFAULT_PIPX_GLOBAL_BIN_DIR} and can be overridden by
            setting the environment variable `PIPX_GLOBAL_BIN_DIR`.

            The default manual pages location is {paths.DEFAULT_PIPX_MAN_DIR} and
            can be overridden by setting the environment variable `PIPX_MAN_DIR`.
            If the `--global` option is used, the default manual pages location
            instead is {paths.DEFAULT_PIPX_GLOBAL_MAN_DIR} and can be overridden
            by setting the environment variable `PIPX_GLOBAL_MAN_DIR`.

            The default python executable used to install a package is
            {os.getenv("PIPX__DOC_DEFAULT_PYTHON", get_default_python_spec())} and can be overridden
            by setting the environment variable `PIPX_DEFAULT_PYTHON`.
            """
        ),
        parents=[shared_parser],
    )
    parser.add_argument("package_spec", help="package name(s), PEP 723 script(s), or installation spec(s)", nargs="+")
    _add_dependency_app_options(parser)
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help=_FORCE_INSTALL_HELP,
    )
    parser.add_argument(
        "--upgrade",
        "-U",
        action="store_true",
        help=(
            "Upgrade or downgrade an existing package when its version does not satisfy the supplied spec, "
            "removing exposed apps, manual pages, and shell completions the new version no longer ships"
        ),
    )
    parser.add_argument(
        "--upgrade-strategy",
        choices=["only-if-needed", "eager"],
        help="How dependency upgrades are handled when --upgrade changes an existing package",
    )
    parser.add_argument(
        "--suffix",
        default="",
        help=(
            "Optional suffix for virtual environment and executable names. It goes at the end of each app name "
            "(pip3.14 becomes pip3.14_a), before the file extension on Windows (pip3.14_a.exe, hello_a.py)."
        ),
    )
    _add_python_options(parser)
    parser.add_argument(
        "--preinstall",
        action="append",
        type=_package_spec,
        help=(
            "Optional package to be installed into the Virtual Environment before "
            "installing the main package. Use this flag multiple times if you want to preinstall multiple packages."
        ),
    )
    parser.add_argument(
        "--app",
        action="append",
        help="Require this application entry point after installation. Repeat to require multiple entry points.",
    )
    parser.add_argument(
        "--lock",
        type=Path,
        help="Install the environment from an explicit pylock.toml file.",
    )
    _add_pip_venv_args(parser)
    _add_backend_arg(parser)
    _add_output_option(parser)
    parser.set_defaults(func=_cmd_install)


def _add_dependency_app_options(parser: argparse.ArgumentParser) -> None:
    group: Final[argparse._MutuallyExclusiveGroup] = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--include-deps",
        help="Include apps and manual pages from all dependencies",
        action="store_true",
    )
    group.add_argument(
        "--include-resources-from",
        action="append",
        default=[],
        metavar="PACKAGE",
        help="Include apps and manual pages from this dependency. Repeat for multiple dependencies",
    )


def _add_python_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--python",
        help=(
            "Python to install with. Possible values can be the executable name (python3.11), "
            "the version of an available system Python or to pass to py launcher (3.11), "
            f"or the full path to the executable. Requires Python {MINIMUM_PYTHON_VERSION} or above."
        ),
    )
    fetch_python_group: Final[argparse._MutuallyExclusiveGroup] = parser.add_mutually_exclusive_group()
    fetch_python_group.add_argument(
        "--fetch-python",
        type=FetchPythonOptions,
        choices=list(FetchPythonOptions),
        default=_FETCH_PYTHON,
        help=(
            f"When to fetch a standalone Python build from python-build-standalone. "
            f"'{FetchPythonOptions.ALWAYS}' uses a standalone build even when a system Python matches; "
            f"'{FetchPythonOptions.MISSING}' downloads only when the requested version is not found locally; "
            f"'{FetchPythonOptions.NEVER}' never downloads. "
            "Defaults to PIPX_FETCH_PYTHON, or 'never'."
        ),
    )
    fetch_python_group.add_argument(
        "--fetch-missing-python",
        dest="fetch_python",
        action=_DeprecatedFetchMissingPython,
        help="Deprecated: alias for --fetch-python=missing.",
    )


class _DeprecatedFetchMissingPython(argparse.Action):
    def __init__(self, option_strings: list[str], dest: str, **kwargs: Any) -> None:  # ruff:ignore[any-type]  # argparse kwargs
        super().__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[str] | None,
        option_string: str | None = None,
    ) -> None:
        del parser, values
        if not {"--help", "-h"}.intersection(sys.argv):
            print(  # ruff:ignore[print]  # user-facing CLI output
                f"{HAZARD} {option_string} is deprecated; use --fetch-python={FetchPythonOptions.MISSING} instead.",
                file=sys.stderr,
            )
        setattr(namespace, self.dest, FetchPythonOptions.MISSING)


def _package_spec(value: str) -> str:
    # pip and uv would read a dash-leading value as one of their own options rather than a package
    if value.startswith("-"):
        msg = f"{redact_url_credentials(value)!r} is an installer option; pass it with --pip-args"
        raise argparse.ArgumentTypeError(msg)
    return value


def _add_pip_venv_args(parser: argparse.ArgumentParser, system_site_packages_note: str = "") -> None:
    parser.add_argument(
        "--system-site-packages",
        action="store_true",
        help=f"Give the virtual environment access to the system site-packages dir.{system_site_packages_note}",
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
        help=(
            "Arbitrary pip arguments to pass directly to pip install/upgrade commands. "
            "Under the uv backend, `pipx run` translates a subset (--index-url/-i, --extra-index-url, "
            "--find-links/-f, --trusted-host, --no-binary, --only-binary, --pre, --upgrade/-U, "
            "--no-cache-dir) and rejects other flags; other commands pass them to `uv pip install` unchanged."
        ),
    )
    parser.add_argument(
        "--cooldown",
        type=_non_negative_int,
        metavar="DAYS",
        help="Ignore index artifacts uploaded fewer than DAYS days ago. Defaults to PIPX_COOLDOWN; pass 0 to opt out.",
    )


def _non_negative_int(value: str) -> int:
    with contextlib.suppress(ValueError):
        if (days := int(value)) >= 0:
            return days
    msg = "--cooldown must be a non-negative integer"
    raise argparse.ArgumentTypeError(msg)


def _add_backend_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--backend",
        choices=list(KNOWN_BACKENDS),
        default=None,
        help=(
            "Backend used for creating venvs and managing packages. Defaults to "
            "PIPX_DEFAULT_BACKEND when set, else 'uv' when uv is available "
            "(via the `pipx[uv]` extra or on PATH), else 'pip'. Commands on an existing venv keep its "
            "recorded backend and warn when this flag differs; `pipx reinstall` and `pipx reinstall-all` "
            "rebuild venvs with it."
        ),
    )


def _add_output_option(parser: argparse.ArgumentParser, *, snapshot_json: bool = False) -> None:
    group: Final[argparse._MutuallyExclusiveGroup] = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--output",
        choices=[output.value for output in OutputFormat],
        default=OutputFormat.HUMAN,
        help="Select the output format.",
    )
    # only ``list`` keeps a ``--json`` flag: it prints the versioned package snapshot that ``install-all`` reads back,
    # which predates and differs from the ``--output json`` result envelope
    if snapshot_json:
        group.add_argument(
            "--json",
            action="store_const",
            const=OutputFormat.JSON,
            dest="output",
            help="Print the installed-package snapshot as JSON, the format install-all consumes.",
        )


def _cmd_install(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[InstallData]:
    from pipx.commands.install import install

    return install(
        None,
        None,
        args.package_spec,
        InstallOptions(
            local_bin_dir=paths.CTX.bin_dir,
            local_man_dir=paths.CTX.man_dir,
            python=ctx.python,
            pip_args=ctx.pip_args,
            venv_args=ctx.venv_args,
            verbose=ctx.verbose,
            force=args.force,
            upgrade=args.upgrade,
            reinstall=False,
            exposure=ExposureOptions(
                include_dependencies=args.include_deps,
                include_resources_from=args.include_resources_from,
                suffix=args.suffix,
            ),
            preinstall_packages=args.preinstall,
            expected_apps=args.app or (),
            lock_file=args.lock,
            python_flag_passed=ctx.python_flag_passed,
            fetch_python=ctx.fetch_python,
            backend=ctx.backend,
            upgrade_strategy=args.upgrade_strategy,
            cooldown=ctx.cooldown,
            emit_output=False,
        ),
    )


def _add_install_all(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "install-all",
        help="Install all packages",
        formatter_class=_LineWrapRawTextHelpFormatter,
        description=(
            "Installs all the packages according to spec metadata file. Installs up to eight environments at once "
            "and prints the output of each in turn, in file order; --verbose installs them one at a time."
        ),
        parents=[shared_parser],
    )
    parser.add_argument("spec_metadata_file", help="Spec metadata file generated from pipx list --output json")
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help=_FORCE_INSTALL_HELP,
    )
    _add_python_options(parser)
    _add_pip_venv_args(parser)
    _add_backend_arg(parser)
    parser.set_defaults(func=_cmd_install_all)


def _cmd_install_all(args: argparse.Namespace, ctx: _DispatchContext) -> ExitCode:
    from pipx.commands.install import install_all

    return install_all(
        args.spec_metadata_file,
        InstallOptions(
            local_bin_dir=paths.CTX.bin_dir,
            local_man_dir=paths.CTX.man_dir,
            python=ctx.python,
            pip_args=ctx.pip_args,
            venv_args=ctx.venv_args,
            verbose=ctx.verbose,
            force=args.force,
            backend=ctx.backend,
            cooldown=ctx.cooldown,
            python_flag_passed=ctx.python_flag_passed,
        ),
    )


def _add_uninject(
    subparsers: argparse._SubParsersAction,
    venv_completer: _VenvCompleter,
    shared_parser: argparse.ArgumentParser,
) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "uninject",
        help="Uninstall injected packages from an existing Virtual Environment",
        description="Uninstalls injected packages from an existing pipx-managed virtual environment.",
        parents=[shared_parser],
    )
    _complete_with(
        parser.add_argument(
            "package", metavar="ENVIRONMENT", help="Name of the existing pipx-managed environment to uninject from"
        ),
        venv_completer,
    )
    parser.add_argument(
        "dependencies",
        nargs="+",
        help="the package names to uninject from the environment",
    )
    parser.add_argument(
        "--leave-deps",
        action="store_true",
        help="Only uninstall the main injected package but leave its dependencies installed.",
    )
    _add_output_option(parser)
    parser.set_defaults(func=_cmd_uninject)


def _complete_with(action: argparse.Action, completer: _VenvCompleter) -> None:
    # argcomplete reads the completer off the action, an attribute argparse does not declare
    cast("_CompletableAction", action).completer = completer


class _CompletableAction(typing.Protocol):
    completer: _VenvCompleter


def _cmd_uninject(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[InjectionData]:
    venv_dir: Final[Path] = _venv_dir(args, ctx)
    with ctx.venv_container.venv_lock(venv_dir):
        from pipx.commands.uninject import uninject

        return uninject(
            venv_dir,
            args.dependencies,
            UninjectOptions(
                local_bin_dir=paths.CTX.bin_dir,
                local_man_dir=paths.CTX.man_dir,
                leave_deps=args.leave_deps,
                verbose=ctx.verbose,
            ),
        )


def _venv_dir(args: argparse.Namespace, ctx: _DispatchContext) -> Path:
    venv_dir: Final[Path] = ctx.venv_container.get_venv_dir(valid_pypi_name(args.package) or args.package)
    _LOGGER.info("Virtual Environment location is %s", venv_dir)
    return venv_dir


def _add_inject(
    subparsers: argparse._SubParsersAction,
    venv_completer: _VenvCompleter,
    shared_parser: argparse.ArgumentParser,
) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "inject",
        help="Install packages into an existing Virtual Environment",
        description="Installs packages to an existing pipx-managed virtual environment.",
        parents=[shared_parser],
    )
    _complete_with(
        parser.add_argument(
            "package", metavar="ENVIRONMENT", help="Name of the existing pipx-managed environment to inject into"
        ),
        venv_completer,
    )
    parser.add_argument(
        "dependencies",
        nargs="*",
        help="the packages to inject into the environment--either package name or pip package spec",
    )
    parser.add_argument(
        "-r",
        "--requirement",
        dest="requirements",
        action="append",
        default=[],
        metavar="file",
        help=(
            "file containing the packages to inject into the Virtual Environment--"
            "one package name or pip package spec per line. "
            "May be specified multiple times."
        ),
    )
    parser.add_argument(
        "--include-apps",
        action="store_true",
        help="Add apps from the injected packages onto your PATH and expose their manual pages",
    )
    _add_dependency_app_options(parser)
    _add_pip_venv_args(parser, _IGNORED_ON_EXISTING_VENV)
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Modify existing virtual environment and files in PIPX_BIN_DIR and PIPX_MAN_DIR",
    )
    parser.add_argument(
        "--with-suffix",
        action="store_true",
        help="Add the suffix (if given) of the Virtual Environment to the packages to inject",
    )
    _add_backend_arg(parser)
    _add_output_option(parser)
    parser.set_defaults(func=_cmd_inject)


def _cmd_inject(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[InjectionData]:
    _warn_ignored_venv_args(ctx, "inject")
    venv_dir: Final[Path] = _venv_dir(args, ctx)
    with ctx.venv_container.venv_lock(venv_dir):
        from pipx.commands.inject import inject

        return inject(
            venv_dir,
            args.dependencies,
            args.requirements,
            InjectOptions(
                pip_args=ctx.pip_args,
                verbose=ctx.verbose,
                include_apps=args.include_apps,
                include_dependencies=args.include_deps,
                include_resources_from=args.include_resources_from,
                force=args.force,
                with_suffix=args.with_suffix,
                backend=ctx.backend,
                cooldown_days=ctx.cooldown.days,
                emit_output=False,
            ),
        )


def _warn_ignored_venv_args(ctx: _DispatchContext, command: str) -> None:
    if ctx.venv_args:
        _LOGGER.warning(
            "%s  Ignoring %s: %s works on existing environments, whose venv options were set by install",
            HAZARD,
            ", ".join(ctx.venv_args),
            command,
        )


def _add_expose(
    subparsers: argparse._SubParsersAction,
    venv_completer: _VenvCompleter,
    shared_parser: argparse.ArgumentParser,
) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "expose",
        help="Relink hidden or missing resources of an environment",
        description="Link each missing app, manual page, and shell completion without rebuilding the environment.",
        parents=[shared_parser],
    )
    _complete_with(parser.add_argument("package", metavar="ENVIRONMENT", help="Environment to expose"), venv_completer)
    _add_output_option(parser)
    parser.set_defaults(func=_cmd_expose)


def _cmd_expose(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[ExposureData]:
    venv_dir: Final[Path] = _venv_dir(args, ctx)
    with ctx.venv_container.venv_lock(venv_dir):
        from pipx.commands.expose import expose

        return expose(venv_dir, paths.CTX.bin_dir, paths.CTX.man_dir, verbose=ctx.verbose)


def _add_unexpose(
    subparsers: argparse._SubParsersAction,
    venv_completer: _VenvCompleter,
    shared_parser: argparse.ArgumentParser,
) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "unexpose",
        help="Hide resources without removing an environment",
        description="Remove global links or copies while retaining the managed environment.",
        parents=[shared_parser],
    )
    _complete_with(parser.add_argument("package", metavar="ENVIRONMENT", help="Environment to hide"), venv_completer)
    _add_output_option(parser)
    parser.set_defaults(func=_cmd_unexpose)


def _cmd_unexpose(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[ExposureData]:
    venv_dir: Final[Path] = _venv_dir(args, ctx)
    with ctx.venv_container.venv_lock(venv_dir):
        from pipx.commands.expose import unexpose

        return unexpose(venv_dir, paths.CTX.bin_dir, paths.CTX.man_dir, verbose=ctx.verbose)


def _add_pin(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "pin",
        help="Pin the specified package to prevent it from being upgraded",
        description="Pin the specified package to prevent it from being upgraded",
        parents=[shared_parser],
    )
    parser.add_argument("package", metavar="ENVIRONMENT", help="Environment to pin")
    parser.add_argument(
        "--injected-only",
        action="store_true",
        help=(
            "Pin injected packages in venv only, so that they will not be upgraded during upgrade operations. "
            "Note that this should not be passed if you wish to pin both main package and injected packages."
        ),
    )
    parser.add_argument(
        "--skip",
        nargs="+",
        default=[],
        help="Skip these packages. Implies `--injected-only`.",
    )
    _add_output_option(parser)
    parser.set_defaults(func=_cmd_pin)


def _cmd_pin(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[PinData]:
    venv_dir: Final[Path] = _venv_dir(args, ctx)
    with ctx.venv_container.venv_lock(venv_dir):
        from pipx.commands.pin import pin

        return pin(venv_dir, ctx.skip_list, verbose=ctx.verbose, injected_only=args.injected_only)


def _add_unpin(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "unpin",
        help="Unpin the specified package",
        description="Unpin the specified package and all injected packages in its venv to allow them to be upgraded",
        parents=[shared_parser],
    )
    parser.add_argument("package", metavar="ENVIRONMENT", help="Environment to unpin")
    _add_output_option(parser)
    parser.set_defaults(func=_cmd_unpin)


def _cmd_unpin(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[PinData]:
    venv_dir: Final[Path] = _venv_dir(args, ctx)
    with ctx.venv_container.venv_lock(venv_dir):
        from pipx.commands.pin import unpin

        return unpin(venv_dir, verbose=ctx.verbose)


def _add_upgrade(
    subparsers: argparse._SubParsersAction,
    venv_completer: _VenvCompleter,
    shared_parser: argparse.ArgumentParser,
) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "upgrade",
        help="Upgrade a package",
        description=(
            "Upgrade package(s) in pipx-managed Virtual Environment(s) by running 'pip install --upgrade PACKAGE' "
            "('uv pip install --upgrade PACKAGE' under the uv backend). "
            "Apps, manual pages, and shell completions the new version adds are exposed, and those it no longer "
            "ships are removed."
        ),
        parents=[shared_parser],
    )
    _complete_with(parser.add_argument("packages", help="names of the packages to upgrade", nargs="+"), venv_completer)
    parser.add_argument(
        "--include-injected",
        action="store_true",
        help="Also upgrade packages injected into the main app's environment",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Modify existing virtual environment and files in PIPX_BIN_DIR and PIPX_MAN_DIR",
    )
    _add_pip_venv_args(parser, " Only used with --install.")
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install package spec if missing",
    )
    _add_python_options(parser)
    _add_backend_arg(parser)
    _add_output_option(parser)
    parser.set_defaults(func=_cmd_upgrade)


def _cmd_upgrade(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[UpgradeData]:
    from pipx.commands.upgrade import upgrade

    return upgrade(
        _venv_dirs(args, ctx),
        UpgradeOptions(
            python=ctx.python,
            pip_args=ctx.pip_args,
            venv_args=ctx.venv_args,
            verbose=ctx.verbose,
            include_injected=args.include_injected,
            force=args.force,
            install=args.install,
            python_flag_passed=ctx.python_flag_passed,
            backend=ctx.backend,
            cooldown=ctx.cooldown,
        ),
    )


def _venv_dirs(args: argparse.Namespace, ctx: _DispatchContext) -> dict[str, Path]:
    venv_dirs: Final[dict[str, Path]] = {
        pkg: ctx.venv_container.get_venv_dir(valid_pypi_name(pkg) or pkg) for pkg in args.packages
    }
    _LOGGER.info(
        "Virtual Environment locations are:\n%s", "\n".join(f"- {key} : {value}" for key, value in venv_dirs.items())
    )
    return venv_dirs


def _add_upgrade_all(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "upgrade-all",
        help="Upgrade all packages.",
        description=(
            "Upgrades all packages within their virtual environments by running 'pip install --upgrade PACKAGE' "
            "('uv pip install --upgrade PACKAGE' under the uv backend). "
            "Apps, manual pages, and shell completions a new version adds are exposed, and those it no longer "
            "ships are removed. Upgrades up to eight environments at once and prints the output of each in turn; "
            "--verbose upgrades them one at a time."
        ),
        parents=[shared_parser],
    )
    parser.add_argument(
        "--include-injected",
        action="store_true",
        help="Also upgrade packages injected into the main app's environment",
    )
    parser.add_argument("--skip", nargs="+", default=[], help="skip these packages")
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Modify existing virtual environment and files in PIPX_BIN_DIR and PIPX_MAN_DIR",
    )
    _add_pip_venv_args(parser, _IGNORED_ON_EXISTING_VENV)
    _add_backend_arg(parser)
    _add_output_option(parser)
    parser.set_defaults(func=_cmd_upgrade_all)


def _cmd_upgrade_all(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[UpgradeData]:
    _warn_ignored_venv_args(ctx, "upgrade-all")
    from pipx.commands.upgrade import upgrade_all

    return upgrade_all(
        ctx.venv_container,
        UpgradeOptions(
            verbose=ctx.verbose,
            include_injected=args.include_injected,
            skip=ctx.skip_list,
            force=args.force,
            pip_args=ctx.pip_args,
            python_flag_passed=ctx.python_flag_passed,
            backend=ctx.backend,
            cooldown=ctx.cooldown,
        ),
    )


def _add_upgrade_shared(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "upgrade-shared",
        help="Upgrade shared libraries.",
        description="Upgrade shared libraries now. Other commands refresh them once they are over 30 days old.",
        parents=[shared_parser],
    )
    parser.add_argument(
        "--pip-args",
        help="Arbitrary pip arguments to pass directly to pip install/upgrade commands",
    )
    _add_output_option(parser)
    parser.set_defaults(func=_cmd_upgrade_shared)


def _cmd_upgrade_shared(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[SharedData]:
    del args
    from pipx.commands.upgrade import upgrade_shared

    return upgrade_shared(ctx.pip_args, verbose=ctx.verbose)


def _add_uninstall(
    subparsers: argparse._SubParsersAction,
    venv_completer: _VenvCompleter,
    shared_parser: argparse.ArgumentParser,
) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "uninstall",
        help="Uninstall a package",
        description=(
            "Uninstalls a pipx-managed Virtual Environment by deleting it and any files that point to its apps."
        ),
        parents=[shared_parser],
    )
    _complete_with(parser.add_argument("package", metavar="ENVIRONMENT"), venv_completer)
    _add_output_option(parser)
    parser.set_defaults(func=_cmd_uninstall)


def _cmd_uninstall(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[UninstallData]:
    venv_dir: Final[Path] = _venv_dir(args, ctx)
    with ctx.venv_container.venv_lock(venv_dir):
        from pipx.commands.uninstall import uninstall

        return uninstall(venv_dir, paths.CTX.bin_dir, paths.CTX.man_dir, verbose=ctx.verbose)


def _add_uninstall_all(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "uninstall-all",
        help="Uninstall all packages",
        description="Uninstall all pipx-managed packages",
        parents=[shared_parser],
    )
    _add_output_option(parser)
    parser.set_defaults(func=_cmd_uninstall_all)


def _cmd_uninstall_all(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[UninstallData]:
    del args
    from pipx.commands.uninstall import uninstall_all

    return uninstall_all(ctx.venv_container, paths.CTX.bin_dir, paths.CTX.man_dir, verbose=ctx.verbose)


def _add_reset(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "reset",
        help="Return pipx to a fresh install",
        description=(
            "Uninstall every pipx-managed package and remove the shared libraries, the caches, the standalone "
            "interpreters, the logs and the trash, which returns pipx to the state it had when it was installed."
        ),
        parents=[shared_parser],
    )
    parser.add_argument("--yes", "-y", action="store_true", help="Reset without asking for confirmation")
    parser.add_argument("--dry-run", action="store_true", help="Report what a reset would remove and stop")
    _add_output_option(parser)
    parser.set_defaults(func=_cmd_reset)


def _cmd_reset(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[ResetData]:
    if not args.dry_run and not args.yes and not _confirmed_reset(_output_format(args)):
        msg = "Reset cancelled."
        raise PipxError(msg)
    from pipx.commands.reset import reset

    return reset(
        ctx.venv_container,
        paths.CTX.bin_dir,
        paths.CTX.man_dir,
        verbose=ctx.verbose,
        dry_run=args.dry_run,
    )


def _confirmed_reset(output: OutputFormat) -> bool:
    if not sys.stdin or not sys.stdin.isatty():
        msg = "Pass --yes to reset when no terminal can confirm it."
        raise PipxError(msg)
    prompt: Final[str] = f"Remove every pipx-installed package and reset pipx's data under {paths.CTX.home}? [y/N] "
    if output is OutputFormat.JSON:
        print(prompt, end="", file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output
    try:
        answer: Final[str] = input("" if output is OutputFormat.JSON else prompt)
    except EOFError:
        return False
    return answer.strip().casefold() in {"y", "yes"}


def _output_format(args: argparse.Namespace) -> OutputFormat:
    return OutputFormat(getattr(args, "output", OutputFormat.HUMAN))


def _add_reinstall(
    subparsers: argparse._SubParsersAction,
    venv_completer: _VenvCompleter,
    shared_parser: argparse.ArgumentParser,
) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "reinstall",
        formatter_class=_LineWrapRawTextHelpFormatter,
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
    _complete_with(parser.add_argument("package", metavar="ENVIRONMENT"), venv_completer)
    _add_python_options(parser)
    _add_backend_arg(parser)
    _add_output_option(parser)
    parser.set_defaults(func=_cmd_reinstall)


def _cmd_reinstall(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[ReinstallData]:
    venv_dir: Final[Path] = _venv_dir(args, ctx)
    with ctx.venv_container.venv_lock(venv_dir) as venv_lock:
        from pipx.commands.reinstall import reinstall

        return reinstall(venv_dir, _reinstall_options(ctx), venv_lock=venv_lock)


def _reinstall_options(ctx: _DispatchContext) -> ReinstallOptions:
    return ReinstallOptions(
        local_bin_dir=paths.CTX.bin_dir,
        local_man_dir=paths.CTX.man_dir,
        python=ctx.python,
        verbose=ctx.verbose,
        python_flag_passed=ctx.python_flag_passed,
        backend=ctx.backend,
        skip=ctx.skip_list,
    )


def _add_reinstall_all(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "reinstall-all",
        formatter_class=_LineWrapRawTextHelpFormatter,
        help="Reinstall all packages",
        description=textwrap.dedent(
            """
            Reinstalls all packages.

            Packages are uninstalled, then installed with pipx install PACKAGE
            with the same options used in the original install of PACKAGE.
            Run it after upgrading Python to move all your packages to the
            new version.

            Rebuilds up to eight environments at once and prints the output
            of each in turn; --verbose rebuilds them one at a time.

            """
        ),
        parents=[shared_parser],
    )
    _add_python_options(parser)
    parser.add_argument("--skip", nargs="+", default=[], help="skip these packages")
    _add_backend_arg(parser)
    _add_output_option(parser)
    parser.set_defaults(func=_cmd_reinstall_all)


def _cmd_reinstall_all(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[ReinstallData]:
    del args
    from pipx.commands.reinstall import reinstall_all

    return reinstall_all(ctx.venv_container, _reinstall_options(ctx))


def _add_health(
    subparsers: argparse._SubParsersAction,
    venv_completer: _VenvCompleter,
    shared_parser: argparse.ArgumentParser,
) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "health",
        help="Check installed package environments",
        description="Check whether installed package environments can run their Python interpreter.",
        parents=[shared_parser],
    )
    _complete_with(parser.add_argument("packages", nargs="*", help="Installed packages to check"), venv_completer)
    _add_output_option(parser)
    parser.set_defaults(func=_cmd_health)


def _cmd_health(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[HealthData]:
    from pipx.commands.health import health

    return health(ctx.venv_container, _selected_venv_dirs(args, ctx))


def _selected_venv_dirs(args: argparse.Namespace, ctx: _DispatchContext) -> tuple[Path, ...]:
    if args.packages:
        # spellings such as "black" and "Black" resolve to one venv, so drop the repeats
        return tuple(dict.fromkeys(_venv_dirs(args, ctx).values()))
    return tuple(sorted(ctx.venv_container.iter_venv_dirs()))


def _add_repair(
    subparsers: argparse._SubParsersAction,
    venv_completer: _VenvCompleter,
    shared_parser: argparse.ArgumentParser,
) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "repair",
        help="Repair broken package environments",
        description="Reinstall packages whose environments cannot run their Python interpreter.",
        parents=[shared_parser],
    )
    _complete_with(parser.add_argument("packages", nargs="*", help="Installed packages to repair"), venv_completer)
    _add_python_options(parser)
    _add_backend_arg(parser)
    _add_output_option(parser)
    parser.set_defaults(func=_cmd_repair)


def _cmd_repair(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[RepairData]:
    from pipx.commands.health import repair

    return repair(ctx.venv_container, _selected_venv_dirs(args, ctx), _reinstall_options(ctx))


def _add_list(
    subparsers: argparse._SubParsersAction,
    venv_completer: _VenvCompleter,
    shared_parser: argparse.ArgumentParser,
) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "list",
        help="List installed packages",
        description="List packages and apps installed with pipx",
        parents=[shared_parser],
    )
    parser.add_argument(
        "--include-injected",
        action="store_true",
        help="Show packages injected into the main app's environment",
    )
    parser.add_argument("--outdated", action="store_true", help="List packages with an available upgrade.")
    format_group: Final[argparse._MutuallyExclusiveGroup] = parser.add_mutually_exclusive_group()
    format_group.add_argument("--short", action="store_true", help="List packages only.")
    format_group.add_argument(
        "--pinned",
        action="store_true",
        help=(
            "List pinned packages only. Pass --include-injected at the same time to list injected packages "
            "that were pinned."
        ),
    )
    _add_output_option(parser, snapshot_json=True)
    _complete_with(parser.add_argument("packages", nargs="*", help="Installed packages to list"), venv_completer)
    parser.set_defaults(func=_cmd_list)


def _cmd_list(args: argparse.Namespace, ctx: _DispatchContext) -> ExitCode | OperationResult[OutdatedData]:
    venv_dirs: Final[tuple[Path, ...]] = _installed_venv_dirs(args, ctx)
    if args.outdated:
        if args.short or args.pinned:
            msg = "--outdated cannot be combined with --short or --pinned."
            raise PipxError(msg)
        from pipx.commands.outdated import list_outdated

        return list_outdated(ctx.venv_container, venv_dirs, include_injected=args.include_injected)
    output: Final[OutputFormat] = _output_format(args)
    if output is OutputFormat.JSON and (args.short or args.pinned):
        msg = "--output json cannot be combined with --short or --pinned."
        raise PipxError(msg)
    from pipx.commands.list_packages import list_packages

    return list_packages(
        ctx.venv_container,
        venv_dirs,
        ListOptions(
            include_injected=args.include_injected,
            json_format=output is OutputFormat.JSON,
            short_format=args.short,
            pinned_only=args.pinned,
        ),
    )


def _installed_venv_dirs(args: argparse.Namespace, ctx: _DispatchContext) -> tuple[Path, ...]:
    venv_dirs: Final[tuple[Path, ...]] = _selected_venv_dirs(args, ctx)
    for venv_dir in venv_dirs:
        if not venv_dir.is_dir():
            name: Final[str] = venv_dir.name
            msg = f"pipx has no venv for {name!r}; run 'pipx list' to see the installed packages"
            raise PipxError(msg)
    return venv_dirs


def _add_interpreter(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "interpreter",
        help="Interact with interpreters managed by pipx",
        description="Interact with interpreters managed by pipx",
    )
    subcommands: Final[argparse._SubParsersAction] = parser.add_subparsers(
        title="subcommands",
        description="Get help for commands with pipx interpreter COMMAND --help",
        dest="interpreter_command",
    )
    list_parser: Final[argparse.ArgumentParser] = subcommands.add_parser(
        "list",
        help="List available interpreters",
        description="List available interpreters",
        parents=[shared_parser],
    )
    prune_parser: Final[argparse.ArgumentParser] = subcommands.add_parser(
        "prune",
        help="Prune unused interpreters",
        description="Prune unused interpreters",
        parents=[shared_parser],
    )
    upgrade_parser: Final[argparse.ArgumentParser] = subcommands.add_parser(
        "upgrade",
        help="Upgrade installed interpreters to the latest available micro/patch version",
        description="Upgrade installed interpreters to the latest available micro/patch version",
        parents=[shared_parser],
    )
    _add_output_option(list_parser)
    list_parser.set_defaults(func=_cmd_interpreter_list)
    _add_output_option(prune_parser)
    prune_parser.set_defaults(func=_cmd_interpreter_prune)
    _add_output_option(upgrade_parser)
    upgrade_parser.set_defaults(func=_cmd_interpreter_upgrade)
    parser.set_defaults(func=_make_print_help(parser))


def _cmd_interpreter_list(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[InterpreterData]:
    del args
    from pipx.commands.interpreter import list_interpreters

    return list_interpreters(ctx.venv_container)


def _cmd_interpreter_prune(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[InterpreterData]:
    del args
    from pipx.commands.interpreter import prune_interpreters

    return prune_interpreters(ctx.venv_container)


def _cmd_interpreter_upgrade(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[InterpreterData]:
    del args
    from pipx.commands.interpreter import upgrade_interpreters

    return upgrade_interpreters(ctx.venv_container, verbose=ctx.verbose)


def _make_print_help(
    target_parser: argparse.ArgumentParser,
) -> Callable[[argparse.Namespace, _DispatchContext], ExitCode]:
    def _print_help(args: argparse.Namespace, ctx: _DispatchContext) -> ExitCode:
        del args, ctx
        target_parser.print_help()
        return EXIT_CODE_OK

    return _print_help


def _add_cache(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "cache",
        help="Manage cached run environments",
        description="Manage cached run environments",
    )
    subcommands: Final[argparse._SubParsersAction] = parser.add_subparsers(
        title="subcommands",
        description="Get help for commands with pipx cache COMMAND --help",
        dest="cache_command",
    )
    dir_parser: Final[argparse.ArgumentParser] = subcommands.add_parser(
        "dir",
        help="Show the cache directory",
        description="Show the cache directory",
        parents=[shared_parser],
    )
    purge_parser: Final[argparse.ArgumentParser] = subcommands.add_parser(
        "purge",
        help="Remove cached run environments",
        description="Remove cached run environments",
        parents=[shared_parser],
    )
    _add_output_option(dir_parser)
    dir_parser.set_defaults(func=_cmd_cache_dir)
    _add_output_option(purge_parser)
    purge_parser.set_defaults(func=_cmd_cache_purge)
    parser.set_defaults(func=_make_print_help(parser))


def _cmd_cache_dir(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[CacheData]:
    del args, ctx
    from pipx.commands.cache import print_cache_dir

    return print_cache_dir(VenvContainer(paths.CTX.venv_cache))


def _cmd_cache_purge(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[CacheData]:
    del args, ctx
    from pipx.commands.cache import purge_cache

    return purge_cache(VenvContainer(paths.CTX.venv_cache))


def _add_manifest(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "manifest",
        help="Manage tools declared in an explicit manifest",
        description="Manage tools declared in an explicit manifest",
    )
    subcommands: Final[argparse._SubParsersAction] = parser.add_subparsers(
        title="subcommands",
        description="Get help for commands with pipx manifest COMMAND --help",
        dest="manifest_command",
    )
    lock_parser: Final[argparse.ArgumentParser] = subcommands.add_parser(
        "lock",
        help="Resolve a tool manifest with nab",
        description="Resolve each locked tool in an explicit manifest into a separate PEP 751 lock file.",
        parents=[shared_parser],
    )
    lock_parser.add_argument("manifest", type=Path, help="Path to the tool manifest.")
    _add_output_option(lock_parser)
    lock_parser.set_defaults(func=_cmd_lock)
    sync_parser: Final[argparse.ArgumentParser] = subcommands.add_parser(
        "sync",
        help="Apply a tool manifest",
        description="Install, upgrade, or downgrade the tools declared in an explicit manifest.",
        parents=[shared_parser],
    )
    sync_parser.add_argument("manifest", type=Path, help="Path to the tool manifest.")
    sync_parser.add_argument("--prune", action="store_true", help="Uninstall environments absent from the manifest.")
    _add_backend_arg(sync_parser)
    _add_output_option(sync_parser)
    sync_parser.set_defaults(func=_cmd_sync)
    parser.set_defaults(func=_make_print_help(parser))


def _cmd_lock(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[ManifestData]:
    del ctx
    from pipx.commands.manifest import lock_manifest

    return lock_manifest(args.manifest)


def _cmd_sync(args: argparse.Namespace, ctx: _DispatchContext) -> OperationResult[ManifestData]:
    from pipx.commands.manifest import sync_manifest

    return sync_manifest(
        args.manifest,
        ctx.venv_container,
        SyncOptions(
            local_bin_dir=paths.CTX.bin_dir,
            local_man_dir=paths.CTX.man_dir,
            python=ctx.python,
            verbose=ctx.verbose,
            prune=args.prune,
            backend=ctx.backend,
        ),
    )


def _add_run(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "run",
        formatter_class=_RunHelpFormatter,
        help=(
            "Download the latest version of a package to a temporary virtual environment, "
            "then run an app from it. Also compatible with local `__pypackages__` "
            "directory (experimental)."
        ),
        description=textwrap.dedent(
            f"""
            Download the latest version of a package to a temporary virtual environment,
            then run an app from it. The environment will be cached
            and reused for up to {constants.TEMP_VENV_EXPIRATION_THRESHOLD_DAYS} days. This
            means subsequent calls to 'run' for the same package will be faster
            since they can reuse the cached Virtual Environment.

            In support of PEP 582 'run' will use apps found in a local __pypackages__
            directory, if present. This behavior is experimental and is a
            companion tool to pythonloc. pipx may change or remove it
            in a future release. See https://github.com/cs01/pythonloc.
            """
        ),
        parents=[shared_parser],
    )
    cache_group: Final[argparse._MutuallyExclusiveGroup] = parser.add_mutually_exclusive_group()
    cache_group.add_argument(
        "--no-cache",
        action="store_true",
        help="Do not reuse cached virtual environment if it exists",
    )
    cache_group.add_argument(
        "--refresh",
        action="store_true",
        help="Rebuild and cache the virtual environment",
    )
    parser.add_argument(
        "--no-path-check",
        action="store_true",
        help="Do not check whether the app is already on PATH",
    )
    parser.add_argument(
        "--python-args",
        metavar="ARGS",
        type=_split_python_args,
        default=[],
        help="Arguments to pass to the Python interpreter that runs the application",
    )
    parser.add_argument(
        "app_with_args",
        metavar="app ...",
        nargs=argparse.REMAINDER,
        help="app/package name and any arguments to be passed to it",
        default=[],
    )
    parser.add_argument("--path", action="store_true", help="Interpret app name as a local path")
    parser.add_argument(
        "--pypackages",
        action="store_true",
        help="Require app to be run from local __pypackages__ directory",
    )
    parser.add_argument(
        "--with",
        dest="with_",
        action="append",
        type=_package_spec,
        default=[],
        help="Extra dependencies to add to the temporary environment",
    )
    parser.add_argument(
        "--spec",
        help=textwrap.dedent(
            """\
            The package name or specific installation source to install the app from.
            For example `--spec mypackage==2.0.0` or `--spec  git+https://github.com/user/repo.git@branch`
            """
        ),
    )
    _add_python_options(parser)
    _add_pip_venv_args(parser, " Not supported under the uv backend.")
    _add_backend_arg(parser)
    parser.set_defaults(subparser=parser, func=_cmd_run)


class _RunHelpFormatter(_LineWrapRawTextHelpFormatter):
    def _format_args(self, action: argparse.Action, default_metavar: str) -> str:
        # argparse renders a REMAINDER positional as a bare "..." in the usage line; its metavar names the required app
        if action.nargs == argparse.REMAINDER:
            return self._metavar_formatter(action, default_metavar)(1)[0]
        return super()._format_args(action, default_metavar)


def _split_python_args(python_args: str) -> list[str]:
    try:
        return shlex.split(python_args, posix=not WINDOWS)
    except ValueError as exc:
        msg = f"invalid Python arguments: {exc}"
        raise argparse.ArgumentTypeError(msg) from exc


def _cmd_run(args: argparse.Namespace, ctx: _DispatchContext) -> NoReturn:
    from pipx.commands.run import run

    run(
        args.app_with_args[0],
        RunOptions(
            dependencies=args.with_,
            app_args=args.app_with_args[1:],
            python=ctx.python,
            pip_args=ctx.pip_args,
            venv_args=ctx.venv_args,
            is_path=args.path,
            pypackages=args.pypackages,
            verbose=ctx.verbose,
            use_cache=not args.no_cache,
            refresh=args.refresh,
            no_path_check=args.no_path_check,
            backend=ctx.backend,
            cooldown=ctx.cooldown,
            python_args=args.python_args,
            python_flag_passed=ctx.python_flag_passed,
            fetch_python=ctx.fetch_python,
        ),
        spec=ctx.spec,
    )


def _add_execute(
    subparsers: argparse._SubParsersAction,
    venv_completer: _VenvCompleter,
    shared_parser: argparse.ArgumentParser,
) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "exec",
        help="Run an application from an existing pipx environment",
        description="Run an application from an existing pipx environment",
        parents=[shared_parser],
    )
    _complete_with(
        parser.add_argument("package", metavar="ENVIRONMENT", help="Name of the existing pipx environment"),
        venv_completer,
    )
    parser.add_argument("app", metavar="APP", help="Application to run")
    parser.add_argument(
        "app_args",
        nargs=argparse.REMAINDER,
        default=[],
        help="Arguments to pass to the application",
    )
    parser.set_defaults(func=_cmd_execute)


def _cmd_execute(args: argparse.Namespace, ctx: _DispatchContext) -> NoReturn:
    venv_dir: Final[Path] = _venv_dir(args, ctx)
    with ctx.venv_container.venv_lock(venv_dir):
        from pipx.commands.execute import execute

        execute(args.package, venv_dir, args.app, args.app_args)


def _add_runpip(
    subparsers: argparse._SubParsersAction,
    venv_completer: _VenvCompleter,
    shared_parser: argparse.ArgumentParser,
) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "runpip",
        help="Run pip, or `uv pip` under the uv backend, in an existing pipx-managed Virtual Environment",
        description="Run pip, or `uv pip` under the uv backend, in an existing pipx-managed Virtual Environment",
        parents=[shared_parser],
    )
    _complete_with(
        parser.add_argument("package", help="Name of the existing pipx-managed Virtual Environment to run pip in"),
        venv_completer,
    )
    parser.add_argument(
        "pipargs",
        nargs=argparse.REMAINDER,
        default=[],
        help="Arguments to forward to pip command",
    )
    parser.set_defaults(func=_cmd_runpip)


def _cmd_runpip(args: argparse.Namespace, ctx: _DispatchContext) -> ExitCode:
    venv_dir: Final[Path] = _venv_dir(args, ctx)
    with ctx.venv_container.venv_lock(venv_dir):
        from pipx.commands.run_pip import run_pip

        return run_pip(args.package, venv_dir, _split_runpip_args(args.pipargs), verbose=ctx.verbose)


def _split_runpip_args(pip_args: list[str]) -> list[str]:
    # a lone argument holding whitespace is a quoted command line, as in pipx runpip black "install black"
    if len(pip_args) != 1 or not any(char.isspace() for char in pip_args[0]):
        return pip_args
    return shlex.split(pip_args[0], posix=not WINDOWS) or pip_args


def _add_ensurepath(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "ensurepath",
        help=("Ensure directories necessary for pipx operation are in your PATH environment variable."),
        description=(
            "Ensure directory where pipx stores apps is in your "
            "PATH environment variable. Also if pipx was installed via "
            "`pip install --user`, ensure pipx itself is in your PATH. "
            "This command may modify your shell configuration, such as '~/.bashrc', "
            "or the system PATH configuration when used with `--global`."
        ),
        parents=[shared_parser],
    )
    parser.add_argument(
        "--prepend",
        action="store_true",
        help="Prepend directories to your PATH instead of appending. Use it to put pipx apps ahead of system apps.",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help=(
            "Add text to your shell's config file even if it looks like your "
            "PATH already contains paths to pipx and pipx-install apps. With --global, "
            "also replace a system PATH configuration file that holds content pipx did not write."
        ),
    )
    parser.add_argument(
        "--all-shells",
        action="store_true",
        help=("Add directories to PATH in all shells instead of just the current one."),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=("Report what would be added to PATH without modifying PATH or any shell configuration file."),
    )
    parser.set_defaults(func=_cmd_ensurepath)


def _cmd_ensurepath(args: argparse.Namespace, ctx: _DispatchContext) -> ExitCode:
    del ctx
    try:
        from pipx.commands.ensure_path import ensure_pipx_paths

        return ensure_pipx_paths(
            prepend=args.prepend,
            force=args.force,
            all_shells=args.all_shells,
            dry_run=args.dry_run,
            is_global=getattr(args, "is_global", False),
        )
    except Exception as error:  # report any failure editing shell or system PATH config as a message, not a traceback
        _LOGGER.debug("Uncaught Exception:", exc_info=True)
        raise PipxError(str(error), wrap_message=False) from None


def _add_environment(subparsers: argparse._SubParsersAction, shared_parser: argparse.ArgumentParser) -> None:
    parser: Final[argparse.ArgumentParser] = subparsers.add_parser(
        "environment",
        formatter_class=_LineWrapRawTextHelpFormatter,
        help="Print a list of environment variables and paths used by pipx.",
        description=textwrap.dedent(
            """
            Prints the names and current values of environment variables used by pipx,
            followed by internal pipx variables which are derived from the environment
            variables and platform specific default values.

            Available variables:
            """
        )
        + textwrap.fill(", ".join(ENVIRONMENT_VARIABLES), break_long_words=False),
        parents=[shared_parser],
    )
    parser.add_argument(
        "--value",
        "-V",
        choices=ENVIRONMENT_VALUE_CHOICES,
        metavar="VARIABLE",
        help="Print the value of the variable.",
    )
    parser.set_defaults(func=_cmd_environment)


def _cmd_environment(args: argparse.Namespace, ctx: _DispatchContext) -> ExitCode:
    del ctx
    from pipx.commands.environment import environment

    return environment(value=args.value)


_COMPLETION_INSTRUCTIONS: Final[str] = """
If your shell reports register-python-argcomplete as not found,
or you run pipx as a zipapp, first run

    pipx install argcomplete

Add the command for your shell to its config file so the shell
runs it on startup. Then open a new shell, or log in again, for
autocompletion to start working.

bash:
    eval "$(register-python-argcomplete pipx)"

zsh:
    To activate completions in zsh, first mark compinit for autoload
    and run it:

    autoload -U compinit && compinit

    Then enable completions for pipx:

    eval "$(register-python-argcomplete pipx)"

    With argcomplete earlier than v3, also enable bashcompinit in zsh:

    autoload -U bashcompinit
    bashcompinit


tcsh:
    eval `register-python-argcomplete --shell tcsh pipx`

fish:
    # Run this once; it does not belong in the config file
    register-python-argcomplete --shell fish pipx >~/.config/fish/completions/pipx.fish

"""


def _cmd_completions(args: argparse.Namespace, ctx: _DispatchContext) -> ExitCode:
    del args, ctx
    print(textwrap.dedent(_COMPLETION_INSTRUCTIONS))  # ruff:ignore[print]  # user-facing CLI output
    return ExitCode(0)


def parse_pipx_args(parser: argparse.ArgumentParser, args: list[str]) -> argparse.Namespace:
    if args[:1] == ["help"]:
        args = [*args[1:], "--help"]
    if args[:1] == ["inject"]:
        parsed_args: Final[argparse.Namespace] = _get_subparser(parser, "inject").parse_intermixed_args(args[1:])
        parsed_args.command = "inject"
        return parsed_args
    return parser.parse_args(args)


def _get_subparser(parser: argparse.ArgumentParser, command: str) -> argparse.ArgumentParser:
    return next(
        action
        for action in parser._actions  # ruff:ignore[private-member-access]  # no public API for subparsers
        if isinstance(action, argparse._SubParsersAction)  # ruff:ignore[private-member-access]  # no public API for subparsers
    ).choices[command]


def _setup(args: argparse.Namespace) -> None:
    _validate_fetch_python()
    _validate_cooldown()
    _validate_max_logs()
    if "version" in args and args.version:
        print(__version__)  # ruff:ignore[print]  # user-facing CLI output
        sys.exit(0)

    if is_global := not constants.WINDOWS and getattr(args, "is_global", False):
        paths.CTX.make_global()

    verbose: Final[int] = (
        -2 if _output_format(args) is OutputFormat.JSON else getattr(args, "verbose", 0) - getattr(args, "quiet", 0)
    )

    _setup_logging(verbose)
    paths.CTX.log_warnings()

    _LOGGER.debug("%s", time.strftime("%Y-%m-%d %H:%M:%S"))
    _LOGGER.debug("%s", " ".join(map(redact_url_credentials, sys.argv)))
    _LOGGER.info("pipx version is %s", __version__)
    _LOGGER.info("Default python interpreter is '%s'", get_default_python())

    # these only read paths, so they also work for users who cannot write the (global) home
    if args.command not in {"environment", "list"}:
        _create_directories(is_global=is_global)

    empty_trash()

    old_pipx_venv_location: Final[Path] = paths.CTX.venvs / "pipx-app"
    if old_pipx_venv_location.exists():
        _LOGGER.warning(
            pipx_wrap(
                f"""
                {HAZARD}  A virtual environment for pipx was detected at
                {old_pipx_venv_location!s}. The 'pipx-app' package has been
                renamed back to 'pipx'
                (https://github.com/pypa/pipx/issues/82).
                """,
                subsequent_indent=" " * 4,
            )
        )


_FETCH_MISSING_PYTHON_RAW: Final[str | None] = os.environ.get("PIPX_FETCH_MISSING_PYTHON")
_FETCH_PYTHON_RAW: Final[str | None] = os.environ.get("PIPX_FETCH_PYTHON")


def _compute_fetch_python(missing_raw: str | None, python_raw: str | None) -> tuple[FetchPythonOptions, bool]:
    fetch_missing: Final[bool] = (missing_raw or "").strip().lower() not in {"", "0", "false", "f", "no", "n", "off"}
    raw: Final[str] = python_raw or (
        FetchPythonOptions.MISSING.value if fetch_missing else FetchPythonOptions.NEVER.value
    )
    try:
        return FetchPythonOptions(raw), False
    except ValueError:
        return FetchPythonOptions.NEVER, True


_FETCH_PYTHON, _FETCH_PYTHON_INVALID = _compute_fetch_python(_FETCH_MISSING_PYTHON_RAW, _FETCH_PYTHON_RAW)

_COOLDOWN_RAW: Final[str | None] = os.environ.get("PIPX_COOLDOWN")


def _compute_cooldown(raw: str | None) -> tuple[int | None, bool]:
    if raw is None or not (stripped := raw.strip()):
        return None, False
    try:
        days: Final[int] = int(stripped)
    except ValueError:
        return None, True
    return (days, False) if days >= 0 else (None, True)


_COOLDOWN, _COOLDOWN_INVALID = _compute_cooldown(_COOLDOWN_RAW)


_MAX_LOGS_RAW: Final[str | None] = os.environ.get("PIPX_MAX_LOGS")


def _compute_max_logs(raw: str | None) -> tuple[int, bool]:
    if raw is None or not (stripped := raw.strip()):
        return 10, False
    try:
        logs: Final[int] = int(stripped)
    except ValueError:
        return 10, True
    return (logs, False) if logs >= 0 else (10, True)


_MAX_LOGS_INVALID: Final[bool] = _compute_max_logs(_MAX_LOGS_RAW)[1]


def _validate_fetch_python() -> None:
    if _FETCH_PYTHON_INVALID:
        msg = f"PIPX_FETCH_PYTHON must be unset or one of: {', '.join(str(option) for option in FetchPythonOptions)}."
        raise PipxError(msg)
    if _FETCH_MISSING_PYTHON_RAW is not None:
        if _FETCH_PYTHON_RAW is not None:
            msg = "Setting both PIPX_FETCH_MISSING_PYTHON and PIPX_FETCH_PYTHON is invalid."
            raise PipxError(msg)
        print(  # ruff:ignore[print]  # user-facing CLI output
            f"{HAZARD} PIPX_FETCH_MISSING_PYTHON is deprecated; "
            f'use PIPX_FETCH_PYTHON="{FetchPythonOptions.MISSING}" instead.',
            file=sys.stderr,
        )


def _validate_cooldown() -> None:
    if _COOLDOWN_INVALID:
        msg = f"PIPX_COOLDOWN must be unset or a non-negative integer, got {_COOLDOWN_RAW!r}."
        raise PipxError(msg)


def _validate_max_logs() -> None:
    if _MAX_LOGS_INVALID:
        msg = f"PIPX_MAX_LOGS must be unset or a non-negative integer, got {_MAX_LOGS_RAW!r}."
        raise PipxError(msg)


def _setup_logging(verbose: int) -> None:
    pipx_str: Final[str] = BOLD(GREEN("pipx >")) if sys.stdout and sys.stdout.isatty() else "pipx >"
    log_stream: Final[TextIOWrapper] = _setup_log_file()
    paths.CTX.log_file = Path(log_stream.name)

    # configured by hand because importing logging.config pulls socket and pickle into every startup
    stream_handler: Final[logging.StreamHandler[TextIO]] = logging.StreamHandler()
    stream_handler.setLevel(min(max(0, logging.WARNING - 10 * verbose), 50))
    stream_handler.setFormatter(
        logging.Formatter(f"{pipx_str}({{funcName}}:{{lineno}}): {{message}}" if verbose else "{message}", style="{")
    )
    file_handler: Final[logging.FileHandler] = logging.FileHandler(paths.CTX.log_file, encoding="utf-8", delay=True)
    file_handler.stream = log_stream
    file_handler.setFormatter(
        logging.Formatter("{relativeCreated: >8.1f}ms ({funcName}:{lineno}): {message}", style="{")
    )
    pipx_logger: Final[logging.Logger] = logging.getLogger("pipx")
    # a test can run several commands in one process; without this each one stacks another pair of handlers
    for handler in pipx_logger.handlers[:]:
        pipx_logger.removeHandler(handler)
        handler.close()
    pipx_logger.setLevel(logging.DEBUG)
    pipx_logger.addHandler(stream_handler)
    pipx_logger.addHandler(file_handler)


def _setup_log_file() -> TextIOWrapper:
    try:
        return _open_log_file(paths.CTX.logs)
    except PermissionError:
        return _open_log_file(platformdirs.user_log_path("pipx"))


def _open_log_file(pipx_log_dir: Path) -> TextIOWrapper:
    # util.mkdir would log, and logging is not set up yet
    pipx_log_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    # a directory created by an older pipx kept the umask mode; one owned by another account keeps whatever it has
    with contextlib.suppress(OSError):
        pipx_log_dir.chmod(0o700)
    log_stream: Final[TextIOWrapper] = _create_log_file(pipx_log_dir)
    # the validator's parser lets a blank PIPX_MAX_LOGS fall back to the default, where int() would fail on it
    _rotate_logs(Path(log_stream.name), _compute_max_logs(os.getenv("PIPX_MAX_LOGS"))[0])
    return log_stream


def _create_log_file(pipx_log_dir: Path) -> TextIOWrapper:
    datetime_str: Final[str] = time.strftime("%Y-%m-%d_%H.%M.%S")
    counter = 0
    while True:
        with contextlib.suppress(FileExistsError):
            log_stream = open(  # ruff:ignore[open-file-with-context-handler]  # the logging handler owns the stream
                pipx_log_dir / f"cmd_{datetime_str}{f'_{counter}' if counter else ''}.log",
                "x",
                encoding="utf-8",
                opener=open_owner_only,
            )
            break
        counter += 1
    # a concurrent pipx skips deleting a locked log; Windows already refuses to delete a file another process has open
    if not WINDOWS:
        # a filesystem without lock support only loses the protection, never the run
        with contextlib.suppress(OSError):
            fcntl.flock(log_stream, fcntl.LOCK_SH)
    return log_stream


def _rotate_logs(current: Path, max_logs: int) -> None:
    # the current log counts toward the limit and must outlive its run, since a failure points the user at its
    # error log, so 0 keeps that one log
    keep_old: Final[int] = max(max_logs - 1, 0)
    name_pattern: Final[re.Pattern[str]] = re.compile(
        r"cmd_(\d{4}-\d\d-\d\d_\d\d\.\d\d\.\d\d)(?:_(\d+))?(_[a-z]+_errors)?\.log"
    )
    command_logs: dict[tuple[str, int], Path] = {}
    error_logs: list[tuple[tuple[str, int], Path]] = []
    for path in current.parent.glob("cmd_*.log"):
        if path != current and (match := name_pattern.fullmatch(path.name)):
            run = (match[1], int(match[2] or 0))
            if match[3]:
                error_logs.append((run, path))
            else:
                command_logs[run] = path
    ordered: Final[list[tuple[tuple[str, int], Path]]] = sorted(command_logs.items())
    for _, path in ordered[: max(0, len(ordered) - keep_old)]:
        _delete_unless_running(path)
    error_logs.sort()
    for run, path in error_logs[: max(0, len(error_logs) - keep_old)]:
        if run not in command_logs or not command_logs[run].exists():
            _remove_log(path)


def _delete_unless_running(log: Path) -> None:
    if WINDOWS:
        _remove_log(log)
        return
    try:
        stream: Final = log.open("rb")
    except OSError:
        # a log this user cannot read (another user's run, chmod 000, a symlink loop or to a directory) cannot be
        # checked for a running owner; it is old enough to rotate, so remove it
        _remove_log(log)
        return
    with stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        except OSError:
            pass  # no lock support on this filesystem: rotate as if no other pipx were running
        _remove_log(log)


def _remove_log(log: Path) -> None:
    # rotation only tidies up, so a log the directory will not let go of (a shared read-only log dir) stays rather
    # than moving logging to the fallback directory
    with contextlib.suppress(OSError):
        log.unlink()


def _create_directories(*, is_global: bool) -> None:
    try:
        mkdir(paths.CTX.venvs)
        mkdir(paths.CTX.bin_dir)
        mkdir(paths.CTX.man_dir)
        mkdir(paths.CTX.venv_cache)
        mkdir(paths.CTX.standalone_python_cachedir)
    except PermissionError as error:
        fix: Final[str] = (
            "run pipx with sudo, or point PIPX_GLOBAL_HOME, PIPX_GLOBAL_BIN_DIR and PIPX_GLOBAL_MAN_DIR at writable"
            " directories"
            if is_global
            else "point PIPX_HOME, PIPX_BIN_DIR and PIPX_MAN_DIR at writable directories"
        )
        msg = f"Cannot create {error.filename}: permission denied; {fix}."
        # wrapping would split a long path across lines
        raise PipxError(msg, wrap_message=False) from error

    for cachedir in [
        paths.CTX.venv_cache,
        paths.CTX.standalone_python_cachedir,
    ]:
        if not (cachedir_tag := cachedir / "CACHEDIR.TAG").exists():
            _LOGGER.debug("Adding CACHEDIR.TAG to cache directory")
            cachedir_tag.write_text(
                "Signature: 8a477f597d28d172789f06886806bc55\n"
                "# This file is a cache directory tag created by pipx.\n"
                "# For information about cache directory tags, see:\n"
                "#       https://bford.info/cachedir/\n",
                encoding="utf-8",
            )


def check_args(parsed_pipx_args: argparse.Namespace) -> None:
    if parsed_pipx_args.command == "run":
        # argparse.REMAINDER keeps the -- that separates pipx's options from the app's
        if parsed_pipx_args.app_with_args and parsed_pipx_args.app_with_args[0] == "--":
            parsed_pipx_args.app_with_args.pop(0)
        # the app is the first item of the REMAINDER positional, which argparse cannot mark required
        if not parsed_pipx_args.app_with_args:
            parsed_pipx_args.subparser.error("the following arguments are required: app")


def _run_pipx_command(args: argparse.Namespace) -> ExitCode:
    if "package" in args:
        _package_is_url(args.package)
        package_is_path(args.package)
    if "packages" in args:
        for package in args.packages:
            _package_is_url(package)
            package_is_path(package)

    spec: str | None = getattr(args, "spec", None)
    if "package" in args and spec is not None and _package_is_url(spec, raise_error=False) and "#egg=" not in spec:
        spec = f"{spec}#egg={args.package}"

    output: Final[OutputFormat] = _output_format(args)
    python = get_default_python()
    if "python" in args:
        try:
            python = find_python_interpreter(args.python or python, fetch_python=args.fetch_python)
        except InterpreterResolutionError as error:
            _LOGGER.debug("Failed to resolve interpreter:", exc_info=True)
            if output is OutputFormat.JSON:
                raise
            print(  # ruff:ignore[print]  # user-facing CLI output
                pipx_wrap(f"{HAZARD} {error}", subsequent_indent=" " * 4)
            )
            return EXIT_CODE_SPECIFIED_PYTHON_EXECUTABLE_NOT_FOUND

    backend: Final[BackendOptions] = BackendOptions(
        cli=getattr(args, "backend", None) or None, env=env_default_backend()
    )
    _validate_backend_available(backend)

    ctx: Final[_DispatchContext] = _DispatchContext(
        fetch_python=args.fetch_python if "fetch_python" in args else FetchPythonOptions.NEVER,
        verbose=bool(args.verbose) if "verbose" in args else False,
        pip_args=get_pip_args(args),
        venv_args=["--system-site-packages"] if getattr(args, "system_site_packages", False) else [],
        venv_container=VenvContainer(paths.CTX.venvs),
        skip_list=[canonicalize_name(name) for name in args.skip] if "skip" in args else [],
        python=python,
        python_flag_passed=bool(getattr(args, "python", None)),
        spec=spec,
        backend=backend,
        cooldown=CooldownOptions(
            cli_days=getattr(args, "cooldown", None), env_days=_COOLDOWN if "cooldown" in args else None
        ),
    )
    with (
        skip_shared_libs_maintenance(enabled=getattr(args, "skip_maintenance", False)),
        shared_pip_cooldown(ctx.cooldown.days),
        # pip writes its progress to stdout, which under JSON belongs to the envelope alone
        stream_subprocess_stdout_to_stderr(enabled=output is OutputFormat.JSON),
    ):
        result: Final = args.func(args, ctx)
    if isinstance(result, OperationResult):
        return render_result(result, output=output, quiet=getattr(args, "quiet", 0))
    return result


def _package_is_url(package: str, *, raise_error: bool = True) -> bool:
    if (parsed_url := urllib.parse.urlparse(package)).scheme and parsed_url.netloc:
        if not raise_error:
            return True
        msg = "Package cannot be a URL. A valid package name should be passed instead."
        raise PipxError(msg)
    return False


def package_is_path(package: str) -> None:
    if any(separator in package for separator in (os.path.sep, os.path.altsep) if separator):
        raise PipxError(
            pipx_wrap(
                f"""
                Error: '{redact_url_credentials(package)}' looks like a path.
                Expected the name of an installed package.
                """
            )
        )


def _validate_backend_available(backend: BackendOptions) -> None:
    # no auto-detection: it costs a `uv --version` subprocess, also for the commands that never build a backend
    name, source = resolve_backend_name(cli_value=backend.cli, env_value=backend.env, auto=False)
    if source in {"cli", "env"}:
        _LOGGER.info("Backend resolved to %s (source: %s)", name, source)
    # only an explicit --backend uv fails early; a uv picked by the environment stays silent so diagnostic commands,
    # which never build a backend, keep working without it
    if name == UV and source == "cli":
        get_backend(name)


@dataclass(frozen=True, slots=True, kw_only=True)
class _DispatchContext:
    verbose: bool
    pip_args: list[str]
    venv_args: list[str]
    venv_container: VenvContainer
    skip_list: list[str]
    python: str
    python_flag_passed: bool
    spec: str | None
    backend: BackendOptions
    cooldown: CooldownOptions
    fetch_python: FetchPythonOptions


def get_pip_args(args: argparse.Namespace) -> list[str]:
    pip_args: Final[list[str]] = []
    # keep an empty value so reject_empty_index refuses it rather than the backend falling back to its default index
    if (index_url := getattr(args, "index_url", None)) is not None:
        pip_args.extend(["--index-url", index_url])
    if value := getattr(args, "pip_args", None):
        pip_args.extend(_split_pip_args(value))
    # --editable applies to the argument after it, the package spec
    if getattr(args, "editable", False):
        pip_args.append("--editable")
    reject_empty_index(pip_args)
    return pip_args


def _split_pip_args(value: str) -> list[str]:
    # cmd.exe and PowerShell hand the quotes over verbatim, so drop a pair wrapping the whole value; any other pair
    # belongs to one argument, as in --find-links '/tmp/foo bar'
    if len(value) > 1 and value[0] == "'" and value.find("'", 1) == len(value) - 1:
        value = value[1:-1]
    lexer: Final[shlex.shlex] = shlex.shlex(value, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    if WINDOWS:
        # posix=False leaves the quotes inside each token and pip then reads them as part of the path; posix quoting
        # without escapes keeps the backslash a path separator instead
        lexer.escape = ""
    try:
        return list(lexer)
    except ValueError as exc:
        msg = f"invalid pip arguments: {exc}"
        raise PipxError(msg) from exc


def _command_tokens(args: argparse.Namespace) -> tuple[str, ...]:
    tokens: Final[list[str]] = [args.command]
    for subcommand in ("cache_command", "interpreter_command", "manifest_command"):
        if value := getattr(args, subcommand, None):
            tokens.append(value)
    return tuple(tokens)


if __name__ == "__main__":
    sys.exit(cli())


__all__ = [
    "InstalledVenvsCompleter",
    "build_parser",
    "check_args",
    "cli",
    "get_command_parser",
    "get_pip_args",
    "package_is_path",
    "parse_pipx_args",
    "prog_name",
]
