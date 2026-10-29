from __future__ import annotations

__lazy_modules__ = [
    "concurrent.futures",
    "fcntl",
    "itertools",
    "pathlib",
    "pipx.fanout",
    "pipx.redact",
    "pipx.util",
    "pty",
    "re",
    "select",
    "shutil",
    "struct",
    "subprocess",
    "termios",
]

import codecs
import errno
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, suppress
from contextvars import ContextVar, copy_context
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Final,
    NoReturn,
    TextIO,
)

from pipx.animate import show_cursor
from pipx.constants import WINDOWS
from pipx.fanout import output_is_held, stop_process_group, stopped_on_interrupt
from pipx.redact import redact_command_line, redact_url_credentials
from pipx.util import PipxError

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
_STREAM_STDOUT_TO_STDERR: Final[ContextVar[bool]] = ContextVar("stream_stdout_to_stderr", default=False)


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

    _LOGGER.info("exec_app: %s", redact_command_line(cmd))

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

    _LOGGER.info("running %s", redact_command_line(cmd) if log_cmd_str is None else log_cmd_str)
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
    msg = f"{redact_command_line(completed_process.args)!r} failed"
    raise PipxError(msg)


__all__ = [
    "exec_app",
    "get_site_packages",
    "run_pypackage_bin",
    "run_subprocess",
    "stream_subprocess_stdout_to_stderr",
    "subprocess_post_check",
]
