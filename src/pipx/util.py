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
    "re",
    "random",
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
from threading import Lock
from typing import (
    TYPE_CHECKING,
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
    from re import Pattern

if not WINDOWS:
    import fcntl
    import pty
    import select
    import struct
    import termios

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
_STREAM_STDOUT_TO_STDERR: Final[ContextVar[bool]] = ContextVar("stream_stdout_to_stderr", default=False)
# Windows appends by seeking to the end and then writing, so fan-out tasks appending at once overwrite each other
_ERROR_LOG_LOCK: Final[Lock] = Lock()


class PipxError(Exception):
    def __init__(self, message: str, *, wrap_message: bool = True, backend_output: str = "") -> None:
        self.raw_message: Final[str] = message
        # what pip or uv said, for a result envelope to carry when the terminal already showed it live
        self.backend_output: Final[str] = backend_output
        super().__init__(pipx_wrap(message) if wrap_message else message)


class InstalledNameMismatchError(PipxError):
    def __init__(self, installed_name: str) -> None:
        self.installed_name: Final[str] = installed_name
        super().__init__(f"The package spec installed {installed_name!r}, a different name than expected.")


def rmdir(path: Path, *, safe_rm: bool = True) -> None:
    if not path.is_dir():
        return

    _LOGGER.info("removing directory %s", path)
    # Windows refuses to delete a running file but lets it be renamed, so pipx moves a directory that survives to the
    # trash for a later run to delete; ignoring errors keeps a locked file from making cleanup fatal
    shutil.rmtree(path, ignore_errors=True)

    if path.is_dir():
        if safe_rm:
            _LOGGER.warning("Failed to delete %s. Will move it to a temp folder to delete later.", path)

            try:
                path.rename(_get_trash_file(path))
            except OSError as error:
                _LOGGER.warning("Failed to move %s to the trash; remove it by hand (%s).", path, error)
        else:
            _LOGGER.warning("Failed to delete %s. You may need to delete it manually.", path)


def _get_trash_file(path: Path) -> Path:
    paths.CTX.trash.mkdir(exist_ok=True)
    prefix: Final[str] = "".join(random.choices(string.ascii_lowercase, k=8))  # ruff:ignore[suspicious-non-cryptographic-random-usage]  # temp filename, not security-sensitive
    return paths.CTX.trash / f"{prefix}.{path.name}"


def rmdir_via_trash(path: Path) -> None:
    # a removal killed halfway leaves the directory whole or gone from its parent, never partly deleted in place
    try:
        path.rename(trash := _get_trash_file(path))
    except OSError:
        rmdir(path)
    else:
        rmdir(trash)


def mkdir(path: Path) -> None:
    if path.is_dir():
        return
    _LOGGER.info("creating directory %s", path)
    path.mkdir(parents=True, exist_ok=True)


def safe_unlink(file: Path) -> None:
    if not file.is_file() and not file.is_symlink():
        return
    try:
        file.unlink()
    except PermissionError:
        # Windows lets a running file be renamed but not deleted
        file.rename(_get_trash_file(file))


def get_pypackage_bin_path(binary_name: str) -> Path:
    return Path("__pypackages__") / f"{sys.version_info.major}.{sys.version_info.minor}" / "lib" / "bin" / binary_name


def run_pypackage_bin(bin_path: Path, args: list[str]) -> NoReturn:
    exec_app(
        [str(bin_path.resolve()), *args],
        extra_python_paths=[".", str(bin_path.parent.parent)],
    )


def exec_app(
    cmd: Sequence[str | Path],
    env: dict[str, str] | None = None,
    extra_python_paths: list[str] | None = None,
) -> NoReturn:
    environment: Final[dict[str, str]] = _fix_subprocess_env(dict(os.environ) if env is None else env, force_utf8=False)

    if extra_python_paths is not None:
        environment["PYTHONPATH"] = os.path.pathsep.join(
            extra_python_paths + (inherited.split(os.path.pathsep) if (inherited := os.getenv("PYTHONPATH")) else [])
        )

    # the app takes over the terminal, so bring back a cursor a spinner may have hidden
    show_cursor()

    _LOGGER.info("exec_app: %s", _command_line(cmd))

    if WINDOWS:
        sys.exit(subprocess.run(cmd, env=environment, check=False).returncode)
    os.execvpe(str(cmd[0]), [str(x) for x in cmd], environment)  # ruff:ignore[start-process-with-no-shell]  # pipx replaces itself with the requested app by design


def _fix_subprocess_env(env: dict[str, str], *, force_utf8: bool = True) -> dict[str, str]:
    # some platforms (macOS with Homebrew) add pipx directories to PYTHONPATH, which makes pipx's dependencies look
    # installed in the venv (#233), and __PYVENV_LAUNCHER__ can start the wrong python binary (#334)
    for env_to_remove in ("PYTHONPATH", "__PYVENV_LAUNCHER__"):
        env.pop(env_to_remove, None)

    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    if force_utf8:
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONLEGACYWINDOWSSTDIO"] = "utf-8"
    # install into the venv, not the user base or a custom target directory
    env["PIP_USER"] = "0"
    env.pop("PIP_TARGET", None)
    env.setdefault("PIP_KEYRING_PROVIDER", "subprocess")
    return env


def _command_line(cmd: Sequence[str | Path]) -> str:
    return " ".join(redact_url_credentials(str(c)) for c in cmd)


def redact_url_credentials(text: str) -> str:
    # index and package URLs can carry credentials, which must not reach the log file or the verbose output. A bare user
    # such as git@ may be a token, and so may the user before an empty or placeholder password (TOKEN:@), so with a
    # colon both parts are masked.
    #
    # The authority ends at the first /, ? or #, and its userinfo runs to the last @ before that. A password may hold a
    # space, so callers mask each argument before joining a command line; a line break still ends it, as installer
    # output holds a URL per line. Across a space the match can start at a bare token and end at a later word's @, so a
    # user part holding an @ is masked as a bare user.
    return re.sub(
        r"(?<=://)([^/?#\r\n]*)@",
        lambda match: "****:****@" if (userinfo := match[1].partition(":"))[1] and "@" not in userinfo[0] else "****@",
        text,
    )


if WINDOWS:

    def get_venv_paths(root: Path) -> tuple[Path, Path, Path]:
        # the Microsoft Store Python redirects paths for sandboxing, so work from the real root:
        # https://github.com/pypa/pipx/issues/1164
        real_root: Final[Path] = root.resolve()
        bin_path: Final[Path] = real_root / ("bin" if MINGW else "Scripts")
        return bin_path, bin_path / "python.exe", real_root / "share" / "man"

else:

    def get_venv_paths(root: Path) -> tuple[Path, Path, Path]:
        bin_path: Final[Path] = root / "bin"
        return bin_path, bin_path / "python", root / "share" / "man"


def get_site_packages(python: Path) -> list[Path]:
    if (site_packages := _site_packages_from_layout(python.parent.parent)) is not None:
        return site_packages
    purelib, _, platlib = (
        run_subprocess(
            [
                python,
                "-c",
                "import sysconfig; print(sysconfig.get_path('purelib')); print(sysconfig.get_path('platlib'))",
            ],
            capture_stderr=False,
        )
        .stdout.strip()
        .partition("\n")
    )

    purelib_path: Final[Path] = Path(purelib)
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
    env: Final[dict[str, str]] = _fix_subprocess_env(dict(os.environ))
    for key, value in (env_overrides or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value

    _LOGGER.info("running %s", _command_line(cmd) if log_cmd_str is None else log_cmd_str)
    if run_dir:
        Path(run_dir).mkdir(parents=True, exist_ok=True)
    # windows cannot take Path objects, only strings
    cmd_str_list: Final[list[str]] = [str(c) for c in cmd]

    # keeps the working directory off a child Python's sys.path, so a local file cannot shadow a standard library
    # module (#1575)
    if cmd_str_list and "python" in Path(cmd_str_list[0]).name.lower():
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

    # an installer quotes an operand it rejects as typed, so its output can carry the credentials of a URL
    completed_process.stdout, completed_process.stderr = (
        None if output is None else redact_url_credentials(output)
        for output in (completed_process.stdout, completed_process.stderr)
    )
    if capture_stdout and log_stdout and not stream_output:
        _LOGGER.debug(f"stdout: {completed_process.stdout}".rstrip())
    if capture_stderr and log_stderr and not stream_output:
        _LOGGER.debug(f"stderr: {completed_process.stderr}".rstrip())
    _LOGGER.debug("returncode: %s", completed_process.returncode)

    return completed_process


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
            try:
                futures: Final[dict[str, Future[None]]] = {
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


def _open_stream_channel(destination: TextIO) -> _StreamChannel:
    # pip and uv draw a progress bar only onto a terminal, and a pipe hides the one pipx forwards the output to, so
    # hand the child a pseudo-terminal instead whenever the platform offers one
    if not WINDOWS and destination.isatty():
        reader, child = pty.openpty()
        _match_terminal_size(child)
        return _StreamChannel(reader=reader, child=child, terminal=True)
    reader, child = os.pipe()
    return _StreamChannel(reader=reader, child=child, terminal=False)


def _match_terminal_size(child: int) -> None:
    size: Final[os.terminal_size] = shutil.get_terminal_size()
    with suppress(OSError):
        fcntl.ioctl(child, termios.TIOCSWINSZ, struct.pack("HHHH", size.lines, size.columns, 0, 0))


@dataclass(slots=True, kw_only=True)
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


def _tee_subprocess_output(source: int, destination: TextIO, chunks: list[str]) -> None:
    write_error: OSError | UnicodeError | None = None
    pending_carriage_return: bool = False
    for decoded in chain(
        codecs.iterdecode(iter(lambda: _read_stream(source), b""), "utf-8", errors="replace"),
        (None,),
    ):
        chunk = ("\r" if pending_carriage_return else "") + (decoded or "")
        if decoded is not None:
            # hold a trailing \r back until the next read shows whether it starts a \r\n
            pending_carriage_return = chunk.endswith("\r")
            chunk = (chunk[:-1] if pending_carriage_return else chunk).replace("\r\n", "\n")
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


def _read_stream(source: int) -> bytes:
    try:
        return os.read(source, 8 * 1024)
    except OSError as error:
        # a pseudo-terminal reports the departed child this way rather than as an end of file
        if error.errno == errno.EIO:
            return b""
        raise


def _wait_until_drained(reader: int, reading: Future[None]) -> None:
    poll_seconds: Final[float] = 0.01
    while not reading.done() and select.select([reader], [], [], poll_seconds)[0]:
        time.sleep(poll_seconds)


def _without_terminal_escapes(output: str | None) -> str | None:
    # a child colours what it writes to a terminal, or to a pipe under FORCE_COLOR, and the escapes split the words pipx
    # reads out of the captured copy
    if output is None:
        return None
    return re.sub(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[@-Z\\-_])", "", output)


@contextmanager
def stream_subprocess_stdout_to_stderr(*, enabled: bool) -> Generator[None, None, None]:
    token: Final = _STREAM_STDOUT_TO_STDERR.set(enabled)
    try:
        yield
    finally:
        _STREAM_STDOUT_TO_STDERR.reset(token)


def subprocess_post_check(completed_process: subprocess.CompletedProcess[str], *, streamed: bool = False) -> None:
    if not completed_process.returncode:
        return
    # a streamed run already showed its output live
    if not streamed and completed_process.stdout is not None:
        print(completed_process.stdout, file=sys.stdout, end="")  # ruff:ignore[print]  # relays subprocess output to the user
    if not streamed and completed_process.stderr is not None:
        print(completed_process.stderr, file=sys.stderr, end="")  # ruff:ignore[print]  # relays subprocess output to the user
    msg = f"{_command_line(completed_process.args)!r} failed"
    raise PipxError(msg)


def subprocess_post_check_handle_pip_error(
    completed_process: subprocess.CompletedProcess[str],
    tool_name: str = "pip",
    *,
    streamed: bool,
) -> None:
    if not completed_process.returncode:
        return
    _LOGGER.info("%r failed", _command_line(completed_process.args))
    if paths.CTX.log_file is None:
        msg = "Pipx internal error: No log_file present."
        raise PipxError(msg)
    error_file: Final[Path] = paths.CTX.log_file.parent / f"{paths.CTX.log_file.stem}_{tool_name}_errors.log"
    upper_label: Final[str] = tool_name.upper()
    # the fan-out tasks of an -all command append their failures to the same file at once
    with _ERROR_LOG_LOCK, open(error_file, "a", encoding="utf-8", opener=open_owner_only) as error_fh:
        error_fh.write(
            f"{upper_label} STDOUT\n----------\n{completed_process.stdout or ''}"
            f"\n{upper_label} STDERR\n----------\n{completed_process.stderr or ''}"
        )

    _LOGGER.error(
        "Fatal error from %s prevented installation. Full %s output in file:\n    %s", tool_name, tool_name, error_file
    )
    # the pip output analyser's patterns do not match uv's error format, so pipx shows uv's stderr as is, and either
    # tool skips its error lines once the user saw them streamed live
    if tool_name == "pip":
        _analyze_pip_output(completed_process.stdout, completed_process.stderr, streamed=streamed)
    elif not streamed and (
        uv_errors := [line for line in (completed_process.stderr or "").splitlines() if line.strip()]
    ):
        print("\nSome possibly relevant errors from uv install:", file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output
        for line in uv_errors:
            print(f"    {line}", file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output


def open_owner_only(path: str | os.PathLike[str], flags: int) -> int:
    # logs record command lines that can carry secrets, and a global store keeps them under a world-readable /opt/pipx
    return os.open(path, flags, 0o600)


def _analyze_pip_output(pip_stdout: str, pip_stderr: str, *, streamed: bool) -> None:
    failed_build_stdout: list[str] = []
    last_collecting_dep: str | None = None
    # stdout carries these lines only when pip runs without -q
    for line in pip_stdout.split("\n"):
        if failed_match := re.search(r"Failed to build\s+(\S.+)$", line):
            failed_build_stdout = failed_match.group(1).strip().split()
        if collecting_match := re.search(r"^\s*Collecting\s+(\S+)", line):
            last_collecting_dep = collecting_match.group(1)

    # most useful first, each beside a pip line it catches
    relevant_searches: Final[dict[str, Pattern[str]]] = {
        # Package cairo was not found in the pkg-config search path.
        "not_found": re.compile(r"not (?:be )?found", re.IGNORECASE),
        # unable to execute 'gcc': No such file or directory
        "no_such": re.compile(r"no such", re.IGNORECASE),
        # Exception: Unable to find OpenSSL >= 1.0 headers. (Looked here: ...
        "exception_error": re.compile(r"(Exception|Error):\s*\S+"),
        # LINK : fatal error LNK1104: cannot open file 'kernel32.lib'
        "fatal_error": re.compile(r"fatal error", re.IGNORECASE),
        # ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/...
        "conflict_": re.compile(r"conflict", re.IGNORECASE),
        # error: can't copy 'lib\ansible\module_utils\ansible_release.py': doesn't exist ...
        "error_": re.compile(
            r"error:"
            r"(?!.+Command errored out)"
            r"(?!.+failed building wheel for)"
            r"(?!.+could not build wheels? for)"
            r"(?!.+failed to build one or more wheels)"
            r".+[^:]$",
            re.IGNORECASE,
        ),
    }

    relevants_saved: Final[dict[str, str]] = {}
    failed_build_stderr: Final[set[str]] = set()
    for line in pip_stderr.split("\n"):
        if failed_build_match := re.search(r"Failed to build\s+(?!one or more packages)(\S+)", line):
            failed_build_stderr.add(failed_build_match.group(1))

        for category, pattern in relevant_searches.items():
            if pattern.search(line):
                relevants_saved.setdefault(line.strip(), category)
                break

    _log_failed_builds(failed_build_stdout, failed_build_stderr, last_collecting_dep)

    if relevants_saved and not streamed:
        print("\nSome possibly relevant errors from pip install:", file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output

        print_categories: Final[list[str]] = list(relevant_searches)
        relevants_saved_filtered = list(relevants_saved)
        max_relevant_errors: Final[int] = 10
        while len(print_categories) > 1 and len(relevants_saved_filtered) > max_relevant_errors:
            print_categories.pop(-1)
            relevants_saved_filtered = [
                line for line, category in relevants_saved.items() if category in print_categories
            ]

        for line in relevants_saved_filtered:
            print(f"    {line}", file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output


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


def full_package_description(package_name: str, package_spec: str) -> str:
    if package_name == package_spec:
        return redact_url_credentials(package_name)
    return f"{package_name} from spec {redact_url_credentials(package_spec)!r}"


def is_file_name(name: str) -> bool:
    # joined to a directory, ".." names its parent and a separator or a drive leads anywhere
    return name not in {"", ".."} and Path(name).name == name


def reject_empty_index(pip_args: Sequence[str]) -> None:
    # an empty value usually comes from an unset variable, as in --index-url "$INDEX_URL", and uv reads it as the
    # default index
    for position, argument in enumerate(pip_args):
        option, separator, value = argument.partition("=")
        if option not in {"--default-index", "--extra-index-url", "--index", "--index-url", "-i"} or (
            not separator and position + 1 == len(pip_args)
        ):
            continue
        if not (value if separator else pip_args[position + 1]).strip():
            msg = f"{option} is empty; pass the index URL or leave the option out"
            raise PipxError(msg)


__all__ = [
    "InstalledNameMismatchError",
    "PipxError",
    "exec_app",
    "full_package_description",
    "get_pypackage_bin_path",
    "get_site_packages",
    "get_venv_paths",
    "is_file_name",
    "mkdir",
    "open_owner_only",
    "redact_url_credentials",
    "reject_empty_index",
    "rmdir",
    "rmdir_via_trash",
    "run_pypackage_bin",
    "run_subprocess",
    "safe_unlink",
    "stream_subprocess_stdout_to_stderr",
    "subprocess_post_check",
    "subprocess_post_check_handle_pip_error",
]
