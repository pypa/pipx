from __future__ import annotations

__lazy_modules__ = [
    "concurrent.futures",
    "fcntl",
    "itertools",
    "pathlib",
    "pipx",
    "pipx.fanout",
    "pipx.wrap",
    "pty",
    "random",
    "re",
    "select",
    "shutil",
    "string",
    "struct",
    "subprocess",
    "termios",
]

import codecs
import errno
import logging
import os
import random
import re
import shutil
import string
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, suppress
from contextvars import ContextVar, copy_context
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from re import Pattern
from threading import Lock
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    NoReturn,
    TextIO,
)

from pipx import paths
from pipx.animate import show_cursor
from pipx.constants import MINGW, WINDOWS
from pipx.fanout import output_is_held, stop_process_group, stopped_on_interrupt
from pipx.wrap import pipx_wrap

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence
    from concurrent.futures import Future

if not WINDOWS:
    import fcntl
    import pty
    import select
    import struct
    import termios

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
_SUBPROCESS_STREAM_READ_SIZE: Final[int] = 8 * 1024
_STREAM_STDOUT_TO_STDERR: Final[ContextVar[bool]] = ContextVar("stream_stdout_to_stderr", default=False)
# Windows appends by seeking to the end and then writing, so fan-out tasks appending at once overwrite each other
_ERROR_LOG_LOCK: Final[Lock] = Lock()


class PipxError(Exception):
    def __init__(self, message: str, *, wrap_message: bool = True, backend_output: str = "") -> None:
        self.raw_message: Final[str] = message
        # what pip or uv said, for a result envelope to carry when the terminal already showed it live
        self.backend_output: Final[str] = backend_output
        if wrap_message:
            super().__init__(pipx_wrap(message))
        else:
            super().__init__(message)


class InstalledNameMismatchError(PipxError):
    def __init__(self, installed_name: str) -> None:
        self.installed_name: Final[str] = installed_name
        super().__init__(f"The package spec installed {installed_name!r}, a different name than expected.")


@dataclass(frozen=True)
class RelevantSearch:
    pattern: Pattern[str]
    category: str


def _get_trash_file(path: Path) -> Path:
    if not paths.ctx.trash.is_dir():
        paths.ctx.trash.mkdir(exist_ok=True)
    prefix = "".join(random.choices(string.ascii_lowercase, k=8))  # ruff:ignore[suspicious-non-cryptographic-random-usage]  # temp filename, not security-sensitive
    return paths.ctx.trash / f"{prefix}.{path.name}"


def rmdir(path: Path, *, safe_rm: bool = True) -> None:
    if not path.is_dir():
        return

    _LOGGER.info("removing directory %s", path)
    # Windows doesn't let us delete or overwrite files that are being run
    # But it does let us rename/move it. To get around this issue, we can move
    # the file to a temporary folder (to be deleted at a later time)
    # Always ignore errors so locked files don't make cleanup fatal. If the
    # directory is still present afterwards, safe_rm controls whether it is
    # moved to the trash or left in place with a warning.
    shutil.rmtree(path, ignore_errors=True)

    # move it to be deleted later if it still exists
    if path.is_dir():
        if safe_rm:
            _LOGGER.warning("Failed to delete %s. Will move it to a temp folder to delete later.", path)

            try:
                path.rename(_get_trash_file(path))
            except OSError as error:
                _LOGGER.warning("Failed to move %s to the trash; remove it by hand (%s).", path, error)
        else:
            _LOGGER.warning("Failed to delete %s. You may need to delete it manually.", path)


def mkdir(path: Path) -> None:
    if path.is_dir():
        return
    _LOGGER.info("creating directory %s", path)
    path.mkdir(parents=True, exist_ok=True)


def safe_unlink(file: Path) -> None:
    # Windows doesn't let us delete or overwrite files that are being run
    # But it does let us rename/move it. To get around this issue, we can move
    # the file to a temporary folder (to be deleted at a later time)

    if not file.is_file() and not file.is_symlink():
        return
    try:
        file.unlink()
    except PermissionError:
        file.rename(_get_trash_file(file))


def get_pypackage_bin_path(binary_name: str) -> Path:
    return (
        Path("__pypackages__")
        / (str(sys.version_info.major) + "." + str(sys.version_info.minor))
        / "lib"
        / "bin"
        / binary_name
    )


def run_pypackage_bin(bin_path: Path, args: list[str]) -> NoReturn:
    exec_app(
        [str(bin_path.resolve()), *args],
        extra_python_paths=[".", str(bin_path.parent.parent)],
    )


if WINDOWS:

    def get_venv_paths(root: Path) -> tuple[Path, Path, Path]:
        # Make sure to use the real root path. This matters especially on Windows when using the packaged app
        # (Microsoft Store) version of Python, which uses path redirection for sandboxing.
        # See https://github.com/pypa/pipx/issues/1164
        root = root.resolve()
        bin_path = root / "Scripts" if not MINGW else root / "bin"
        python_path = bin_path / "python.exe"
        man_path = root / "share" / "man"
        return bin_path, python_path, man_path

else:

    def get_venv_paths(root: Path) -> tuple[Path, Path, Path]:
        bin_path = root / "bin"
        python_path = bin_path / "python"
        man_path = root / "share" / "man"
        return bin_path, python_path, man_path


def get_site_packages(python: Path) -> list[Path]:
    """Return the interpreter's purelib first, then its platlib when that is a second directory."""
    if (site_packages := _site_packages_from_layout(python.parent.parent)) is not None:
        return site_packages
    output = run_subprocess(
        [
            python,
            "-c",
            "import sysconfig; print(sysconfig.get_path('purelib')); print(sysconfig.get_path('platlib'))",
        ],
        capture_stderr=False,
    ).stdout
    purelib, _, platlib = output.strip().partition("\n")

    purelib_path = Path(purelib)
    # some Linux layouts symlink lib64 to lib, so compare the resolved targets rather than the scheme strings
    if (platlib_path := Path(platlib)).resolve() == purelib_path.resolve():
        return [purelib_path]
    return [purelib_path, platlib_path]


def _site_packages_from_layout(venv: Path) -> list[Path] | None:
    # reading the directories a CPython venv creates spares starting its interpreter; any other layout asks sysconfig
    if (windows_site_packages := venv / "Lib" / "site-packages").is_dir():
        return [windows_site_packages]
    match list(venv.glob("lib/python3*/site-packages")):
        case [purelib]:
            platlib: Final[Path] = venv / "lib64" / purelib.parent.name / "site-packages"
            return [purelib, platlib] if platlib.is_dir() and not platlib.samefile(purelib) else [purelib]
        case _:
            return None


def _fix_subprocess_env(env: dict[str, str], *, force_utf8: bool = True) -> dict[str, str]:
    # Remove PYTHONPATH because some platforms (macOS with Homebrew) add pipx
    #   directories to it, and can make it appear to venvs as though pipx
    #   dependencies are in the venv path (#233)
    # Remove __PYVENV_LAUNCHER__ because it can cause the wrong python binary
    #   to be used (#334)
    env_blocklist = ["PYTHONPATH", "__PYVENV_LAUNCHER__"]
    for env_to_remove in env_blocklist:
        env.pop(env_to_remove, None)

    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    if force_utf8:
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONLEGACYWINDOWSSTDIO"] = "utf-8"
    # Make sure we install packages to venv, not to userbase or a custom target dir
    env["PIP_USER"] = "0"
    env.pop("PIP_TARGET", None)
    env.setdefault("PIP_KEYRING_PROVIDER", "subprocess")
    return env


@contextmanager
def stream_subprocess_stdout_to_stderr(*, enabled: bool) -> Generator[None, None, None]:
    token: Final = _STREAM_STDOUT_TO_STDERR.set(enabled)
    try:
        yield
    finally:
        _STREAM_STDOUT_TO_STDERR.reset(token)


def run_subprocess(  # ruff:ignore[too-many-arguments]  # thin wrapper over subprocess.run exposing its capture and logging switches
    cmd: Sequence[str | Path],
    *,
    capture_stdout: bool = True,
    capture_stderr: bool = True,
    log_cmd_str: str | None = None,
    log_stdout: bool = True,
    log_stderr: bool = True,
    run_dir: str | None = None,
    env_overrides: dict[str, str | None] | None = None,
    stream_output: bool = False,
    interactive: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a command as a subprocess, capturing stderr and stdout.

    ``env_overrides`` keys map to a string (set/replace) or ``None`` (delete). Unless ``interactive``, the child reads
    no input and runs in a process group of its own, which pipx stops as a whole when it is interrupted.
    """
    env = dict(os.environ)
    env = _fix_subprocess_env(env)
    for key, value in (env_overrides or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value

    _LOGGER.info("running %s", _command_line(cmd) if log_cmd_str is None else log_cmd_str)
    if run_dir:
        Path(run_dir).mkdir(parents=True, exist_ok=True)
    # windows cannot take Path objects, only strings
    cmd_str_list = [str(c) for c in cmd]

    # Set PYTHONSAFEPATH to prevent adding CWD to sys.path in subprocess Python commands
    # This prevents local files from shadowing standard library modules (security issue #1575)
    # Supported in Python 3.11+; for earlier versions, the environment variable is ignored
    # but those versions are less commonly used and the risk is lower
    if len(cmd_str_list) > 0 and "python" in Path(cmd_str_list[0]).name.lower():
        env.setdefault("PYTHONSAFEPATH", "1")

    if stream_output:
        completed_process = _run_streaming_subprocess(
            cmd_str_list,
            capture_stdout=capture_stdout,
            capture_stderr=capture_stderr,
            cwd=run_dir,
            env=env,
        )
    elif interactive:
        completed_process = subprocess.run(
            cmd_str_list,
            env=env,
            stdout=subprocess.PIPE if capture_stdout else None,
            stderr=subprocess.PIPE if capture_stderr else None,
            encoding="utf-8",
            errors="replace",
            check=False,
            cwd=run_dir,
        )
    else:
        # a child writing straight to the terminal would cut into the output of the fan-out task whose turn it is
        hold_stderr: Final[bool] = not capture_stderr and output_is_held()
        with (
            subprocess.Popen(
                cmd_str_list,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE if capture_stdout else None,
                stderr=subprocess.PIPE if capture_stderr or hold_stderr else None,
                encoding="utf-8",
                errors="replace",
                text=True,
                cwd=run_dir,
                # a terminal's Ctrl-C then reaches pipx alone, which decides whether the child finishes; a new session
                # rather than just a new group, as the terminal stops a background group reading or writing it
                start_new_session=True,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            ) as process,
            stopped_on_interrupt(process),
        ):
            try:
                stdout, stderr = process.communicate()
            except BaseException:
                # like subprocess.run, so an interrupt does not leave the child running
                process.kill()
                raise
        if hold_stderr:
            sys.stderr.write(stderr)
        completed_process = subprocess.CompletedProcess(
            process.args,
            process.returncode,
            _without_terminal_escapes(stdout),
            None if hold_stderr else _without_terminal_escapes(stderr),
        )

    if capture_stdout and log_stdout and not stream_output:
        _LOGGER.debug(f"stdout: {completed_process.stdout}".rstrip())
    if capture_stderr and log_stderr and not stream_output:
        _LOGGER.debug(f"stderr: {completed_process.stderr}".rstrip())
    _LOGGER.debug("returncode: %s", completed_process.returncode)

    return completed_process


def _without_terminal_escapes(output: str | None) -> str | None:
    # a child colours what it writes to a terminal, or to a pipe under FORCE_COLOR, and the escapes split the words pipx
    # reads out of the captured copy
    if output is None:
        return None
    return re.sub(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[@-Z\\-_])", "", output)


def _command_line(cmd: Sequence[str | Path]) -> str:
    return " ".join(redact_url_credentials(str(c)) for c in cmd)


def redact_url_credentials(text: str) -> str:
    # index and package URLs can carry credentials, which must not reach the log file or the verbose output. A bare user
    # such as git@ may be a token, and so may the user before an empty or placeholder password (TOKEN:@), so with a
    # colon both parts are masked. The authority ends at the first /, ? or #, and its userinfo runs to the last @ before
    # that. A password may hold a space, so callers mask each argument before joining a command line; a line break
    # still ends it, as installer output holds a URL per line. Across a space the match can start at a bare token and
    # end at a later word's @, so a user part holding an @ is masked as a bare user.
    return re.sub(
        r"(?<=://)([^/?#\r\n]*)@",
        lambda match: "****:****@" if (userinfo := match[1].partition(":"))[1] and "@" not in userinfo[0] else "****@",
        text,
    )


def _run_streaming_subprocess(
    cmd: list[str],
    *,
    capture_stdout: bool,
    capture_stderr: bool,
    cwd: str | None,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    stdout_destination: Final[TextIO] = sys.stderr if _STREAM_STDOUT_TO_STDERR.get() else sys.stdout
    # Windows has no pseudo-terminal to hand the child, so it reads a pipe and rich, which pip draws its bar with,
    # takes TTY_COMPATIBLE for the terminal we forward the output to and COLUMNS for a width it cannot measure.
    if stdout_destination.isatty():
        env.setdefault("TTY_COMPATIBLE", "1")
        env.setdefault("COLUMNS", str(shutil.get_terminal_size().columns))
    stdout_chunks: Final[list[str]] = []
    stderr_chunks: Final[list[str]] = []
    channels: Final[dict[str, _StreamChannel]] = {
        name: _open_stream_channel(destination)
        for name, destination, capture in (
            ("stdout", stdout_destination, capture_stdout),
            ("stderr", sys.stderr, capture_stderr),
        )
        if capture
    }
    try:
        with (
            subprocess.Popen(
                cmd,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=channels["stdout"].child if capture_stdout else None,
                stderr=channels["stderr"].child if capture_stderr else None,
                cwd=cwd,
                start_new_session=True,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            ) as process,
            stopped_on_interrupt(process),
            ThreadPoolExecutor(max_workers=2) as executor,
        ):
            for channel in channels.values():
                if not channel.terminal:
                    channel.close_child()
            sinks: Final = {"stdout": (stdout_destination, stdout_chunks), "stderr": (sys.stderr, stderr_chunks)}
            futures: dict[str, Future[None]] = {}
            try:
                futures = {
                    # each reader needs the caller's context to buffer the output of a fan-out task waiting its turn
                    name: executor.submit(copy_context().run, _tee_subprocess_output, channel.reader, *sinks[name])
                    for name, channel in channels.items()
                }
                returncode: Final[int] = process.wait()
                for name, channel in channels.items():
                    if channel.terminal:
                        # macOS discards what a pseudo-terminal still queues once its last child end closes, so hold
                        # ours open until the reader has taken everything the exited child wrote
                        _wait_until_drained(channel.reader, futures[name])
            except BaseException:
                # the readers return only once nothing holds the child's ends, a build backend the child started
                # included, so the whole group must go before the executor joins them
                stop_process_group(process)
                raise
            finally:
                # a pseudo-terminal reader returns only once every child end is closed, so ours must close before the
                # executor joins the readers, also when Ctrl-C lands while the readers start or the child runs
                for channel in channels.values():
                    channel.close_child()
            for future in futures.values():
                future.result()
    finally:
        for channel in channels.values():
            channel.close()
    return subprocess.CompletedProcess(
        cmd,
        returncode,
        _without_terminal_escapes("".join(stdout_chunks) if capture_stdout else None),
        _without_terminal_escapes("".join(stderr_chunks) if capture_stderr else None),
    )


@dataclass
class _StreamChannel:
    reader: int
    child: int
    terminal: bool

    def close_child(self) -> None:
        if self.child != -1:
            os.close(self.child)
            self.child = -1

    def close(self) -> None:
        self.close_child()
        if self.reader != -1:
            os.close(self.reader)
            self.reader = -1


def _open_stream_channel(destination: TextIO) -> _StreamChannel:
    # pip and uv draw a progress bar only onto a terminal, and a pipe hides the one pipx forwards the output to, so
    # hand the child a pseudo-terminal instead whenever the platform offers one
    if not WINDOWS and destination.isatty():
        reader, child = pty.openpty()
        _match_terminal_size(child)
        return _StreamChannel(reader, child, terminal=True)
    reader, child = os.pipe()
    return _StreamChannel(reader, child, terminal=False)


def _match_terminal_size(child: int) -> None:
    size: Final[os.terminal_size] = shutil.get_terminal_size()
    with suppress(OSError):
        fcntl.ioctl(child, termios.TIOCSWINSZ, struct.pack("HHHH", size.lines, size.columns, 0, 0))


def _wait_until_drained(reader: int, reading: Future[None]) -> None:
    poll_seconds: Final[float] = 0.01
    while not reading.done() and select.select([reader], [], [], poll_seconds)[0]:
        time.sleep(poll_seconds)


def _read_stream(source: int) -> bytes:
    try:
        return os.read(source, _SUBPROCESS_STREAM_READ_SIZE)
    except OSError as error:
        # a pseudo-terminal reports the departed child this way rather than as an end of file
        if error.errno == errno.EIO:
            return b""
        raise


def _tee_subprocess_output(source: int, destination: TextIO, chunks: list[str]) -> None:
    write_error: OSError | UnicodeError | None = None
    pending_carriage_return: bool = False
    for decoded in chain(
        codecs.iterdecode(iter(lambda: _read_stream(source), b""), "utf-8", errors="replace"),
        (None,),
    ):
        if decoded is None:
            chunk = "\r" if pending_carriage_return else ""
        else:
            chunk = ("\r" if pending_carriage_return else "") + decoded
            pending_carriage_return = chunk.endswith("\r")
            if pending_carriage_return:
                chunk = chunk[:-1]
            chunk = chunk.replace("\r\n", "\n")
        if not chunk:
            continue
        chunks.append(chunk)
        if write_error is None:
            try:
                destination.write(chunk)
                destination.flush()
            except (OSError, UnicodeError) as error:
                write_error = error
    if write_error is not None:
        raise write_error


def subprocess_post_check(
    completed_process: subprocess.CompletedProcess[str], *, raise_error: bool = True, streamed: bool = False
) -> None:
    if completed_process.returncode:
        # a streamed run already showed its output live
        if not streamed and completed_process.stdout is not None:
            print(completed_process.stdout, file=sys.stdout, end="")  # ruff:ignore[print]  # relays subprocess output to the user
        if not streamed and completed_process.stderr is not None:
            print(completed_process.stderr, file=sys.stderr, end="")  # ruff:ignore[print]  # relays subprocess output to the user
        if raise_error:
            msg = f"{_command_line(completed_process.args)!r} failed"
            raise PipxError(msg)
        _LOGGER.info("%r failed", _command_line(completed_process.args))


def dedup_ordered(input_list: list[tuple[str, Any]]) -> list[tuple[str, Any]]:
    output_list = []
    seen = set()
    for x in input_list:
        if x[0] not in seen:
            output_list.append(x)
            seen.add(x[0])

    return output_list


def analyze_pip_output(pip_stdout: str, pip_stderr: str, *, streamed: bool = False) -> None:
    r"""Extract useful errors from pip output of failed install

    Print the module that failed to build
    Print some of the most relevant errors from the pip output

    Example pip stderr line for each "relevant" type:
        not_found
            Package cairo was not found in the pkg-config search path.
            src/common.h:34:10: fatal error: 'stdio.h' file not found
            The headers or library files could not be found for zlib,
        no_such
            unable to execute 'gcc': No such file or directory
            build\test1.c(2): fatal error C1083: Cannot open include file: 'cpuid.h': No such file ...
        exception_error
            Exception: Unable to find OpenSSL >= 1.0 headers. (Looked here: ...
        fatal_error
            LINK : fatal error LNK1104: cannot open file 'kernel32.lib'
        conflict_
            ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/...
        error_
            error: can't copy 'lib\ansible\module_utils\ansible_release.py': doesn't exist ...
            build\test1.c(4): error C2146: syntax error: missing ';' before identifier 'x'
    """
    max_relevant_errors = 10

    failed_build_stdout: list[str] = []
    last_collecting_dep: str | None = None
    # for any useful information in stdout, `pip install` must be run without
    #   the -q option
    for line in pip_stdout.split("\n"):
        failed_match = re.search(r"Failed to build\s+(\S.+)$", line)
        collecting_match = re.search(r"^\s*Collecting\s+(\S+)", line)
        if failed_match:
            failed_build_stdout = failed_match.group(1).strip().split()
        if collecting_match:
            last_collecting_dep = collecting_match.group(1)

    # In order of most useful to least useful
    relevant_searches = [
        RelevantSearch(re.compile(r"not (?:be )?found", re.IGNORECASE), "not_found"),
        RelevantSearch(re.compile(r"no such", re.IGNORECASE), "no_such"),
        RelevantSearch(re.compile(r"(Exception|Error):\s*\S+"), "exception_error"),
        RelevantSearch(re.compile(r"fatal error", re.IGNORECASE), "fatal_error"),
        RelevantSearch(re.compile(r"conflict", re.IGNORECASE), "conflict_"),
        RelevantSearch(
            re.compile(
                r"error:"
                r"(?!.+Command errored out)"
                r"(?!.+failed building wheel for)"
                r"(?!.+could not build wheels? for)"
                r"(?!.+failed to build one or more wheels)"
                r".+[^:]$",
                re.IGNORECASE,
            ),
            "error_",
        ),
    ]

    failed_stderr_patt = re.compile(r"Failed to build\s+(?!one or more packages)(\S+)")

    relevants_saved = []
    failed_build_stderr = set()
    for line in pip_stderr.split("\n"):
        failed_build_match = failed_stderr_patt.search(line)
        if failed_build_match:
            failed_build_stderr.add(failed_build_match.group(1))

        for relevant_search in relevant_searches:
            if relevant_search.pattern.search(line):
                relevants_saved.append((line.strip(), relevant_search.category))
                break

    _log_failed_builds(failed_build_stdout, failed_build_stderr, last_collecting_dep)

    relevants_saved = dedup_ordered(relevants_saved)

    if relevants_saved and not streamed:
        print("\nSome possibly relevant errors from pip install:", file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output

        print_categories = [x.category for x in relevant_searches]
        relevants_saved_filtered = relevants_saved.copy()
        while (len(print_categories) > 1) and (len(relevants_saved_filtered) > max_relevant_errors):
            print_categories.pop(-1)
            relevants_saved_filtered = [x for x in relevants_saved if x[1] in print_categories]

        for relevant_saved in relevants_saved_filtered:
            print(f"    {relevant_saved[0]}", file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output


def _log_failed_builds(
    failed_build_stdout: list[str],
    failed_build_stderr: set[str],
    last_collecting_dep: str | None,
) -> None:
    if failed_build_stdout:
        failed_to_build_str = "\n    ".join(failed_build_stdout)
        plural_str = "s" if len(failed_build_stdout) > 1 else ""
        print(file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output
        _LOGGER.error("pip failed to build package%s:\n    %s", plural_str, failed_to_build_str)
    elif failed_build_stderr:
        failed_to_build_str = "\n    ".join(failed_build_stderr)
        plural_str = "s" if len(failed_build_stderr) > 1 else ""
        print(file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output
        _LOGGER.error("pip seemed to fail to build package%s:\n    %s", plural_str, failed_to_build_str)
    elif last_collecting_dep is not None:
        print(file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output
        _LOGGER.error("pip seemed to fail to build package:\n    %s", last_collecting_dep)


def open_owner_only(path: str | os.PathLike[str], flags: int) -> int:
    # logs record command lines that can carry secrets, and a global store keeps them under a world-readable /opt/pipx
    return os.open(path, flags, 0o600)


def subprocess_post_check_handle_pip_error(
    completed_process: subprocess.CompletedProcess[str],
    tool_name: str = "pip",
    *,
    streamed: bool = False,
) -> None:
    """Persist subprocess output; run pip-specific heuristics for the pip path.

    ``tool_name="pip"`` keeps the historical wording that log-scrapers /
    tests built around. uv writes a uv-labelled log and skips the pip output
    analyser, whose regexes don't match uv's error format; its stderr is
    printed as is instead. Either tool skips the error lines when ``streamed``
    says the user already saw them live.
    """
    if not completed_process.returncode:
        return
    _LOGGER.info("%r failed", _command_line(completed_process.args))
    if paths.ctx.log_file is None:
        msg = "Pipx internal error: No log_file present."
        raise PipxError(msg)
    error_file = paths.ctx.log_file.parent / f"{paths.ctx.log_file.stem}_{tool_name}_errors.log"
    upper_label = tool_name.upper()
    # the fan-out tasks of an -all command append their failures to the same file at once
    with _ERROR_LOG_LOCK, open(error_file, "a", encoding="utf-8", opener=open_owner_only) as error_fh:
        error_fh.write(
            f"{upper_label} STDOUT\n----------\n{completed_process.stdout or ''}"
            f"\n{upper_label} STDERR\n----------\n{completed_process.stderr or ''}"
        )

    _LOGGER.error(
        "Fatal error from %s prevented installation. Full %s output in file:\n    %s", tool_name, tool_name, error_file
    )
    if tool_name == "pip":
        analyze_pip_output(completed_process.stdout, completed_process.stderr, streamed=streamed)
    elif not streamed and (
        uv_errors := [line for line in (completed_process.stderr or "").splitlines() if line.strip()]
    ):
        print("\nSome possibly relevant errors from uv install:", file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output
        for line in uv_errors:
            print(f"    {line}", file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output


def exec_app(
    cmd: Sequence[str | Path],
    env: dict[str, str] | None = None,
    extra_python_paths: list[str] | None = None,
) -> NoReturn:
    """Run command, do not return

    POSIX: replace current process with command using os.exec*()
    Windows: Use subprocess and sys.exit() to run command
    """

    if env is None:
        env = dict(os.environ)
    env = _fix_subprocess_env(env, force_utf8=False)

    if extra_python_paths is not None:
        env["PYTHONPATH"] = os.path.pathsep.join(
            extra_python_paths + (os.getenv("PYTHONPATH", "").split(os.path.pathsep) if os.getenv("PYTHONPATH") else [])
        )

    # make sure we show cursor again before handing over control
    show_cursor()

    _LOGGER.info("exec_app: %s", _command_line(cmd))

    if WINDOWS:
        sys.exit(subprocess.run(cmd, env=env, check=False).returncode)
    os.execvpe(str(cmd[0]), [str(x) for x in cmd], env)  # ruff:ignore[start-process-with-no-shell]  # pipx replaces itself with the requested app by design


def full_package_description(package_name: str, package_spec: str) -> str:
    if package_name == package_spec:
        return package_name
    return f"{package_name} from spec {redact_url_credentials(package_spec)!r}"


def is_paths_relative(path: Path, parent: Path) -> bool:
    return path.is_relative_to(parent)


def is_file_name(name: str) -> bool:
    # joined to a directory, ".." names its parent and a separator or a drive leads anywhere
    return name not in {"", ".."} and Path(name).name == name


__all__ = [
    "InstalledNameMismatchError",
    "PipxError",
    "RelevantSearch",
    "analyze_pip_output",
    "dedup_ordered",
    "exec_app",
    "full_package_description",
    "get_pypackage_bin_path",
    "get_site_packages",
    "get_venv_paths",
    "is_file_name",
    "is_paths_relative",
    "mkdir",
    "open_owner_only",
    "pipx_wrap",
    "redact_url_credentials",
    "rmdir",
    "run_pypackage_bin",
    "run_subprocess",
    "safe_unlink",
    "stream_subprocess_stdout_to_stderr",
    "subprocess_post_check",
    "subprocess_post_check_handle_pip_error",
]
