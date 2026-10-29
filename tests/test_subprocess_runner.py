from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from io import BytesIO, StringIO, TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING, Final
from venv import EnvBuilder

import pytest

from helpers import SKIP_IF_WINDOWS
from pipx.fanout import fan_out
from pipx.redact import redact_url_credentials
from pipx.subprocess_runner import exec_app, get_site_packages, run_subprocess, subprocess_post_check
from pipx.util import PipxError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from unittest.mock import MagicMock

    from _pytest.capture import CaptureResult
    from pytest_mock import MockerFixture


_UNDECODABLE_OUTPUT: Final[str] = "import os; os.write(1, b'\\xff bad\\n'); os.write(1, b'after\\n')"
_COLOURED_OUTPUT: Final[str] = "satisfy\n\x1b[31m      \x1b[0mPython>=3.12 \x1b]8;;https://x\x07link\x1b]8;;\x1b\\\n"


_STREAM_ENCODING: Final[dict[str, str]] = {"PYTHONIOENCODING": "cp850", "PYTHONLEGACYWINDOWSSTDIO": "cp850"}


def test_exec_app_preserves_stream_encoding_on_posix(mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pipx.subprocess_runner.WINDOWS", False)
    execvpe: Final[MagicMock] = mocker.patch(
        "pipx.subprocess_runner.os.execvpe", autospec=True, side_effect=RuntimeError
    )

    with pytest.raises(RuntimeError):
        exec_app(["python"], dict(_STREAM_ENCODING))

    assert {name: execvpe.call_args.args[2][name] for name in _STREAM_ENCODING} == _STREAM_ENCODING


def test_exec_app_preserves_stream_encoding_on_windows(mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pipx.subprocess_runner.WINDOWS", True)
    run: Final[MagicMock] = mocker.patch(
        "pipx.subprocess_runner.subprocess.run", autospec=True, side_effect=RuntimeError
    )

    with pytest.raises(RuntimeError):
        exec_app(["python"], dict(_STREAM_ENCODING))

    assert {name: run.call_args.kwargs["env"][name] for name in _STREAM_ENCODING} == _STREAM_ENCODING


def test_subprocess_keyring_provider_defaults_to_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PIP_KEYRING_PROVIDER", raising=False)

    result: Final = run_subprocess([sys.executable, "-c", "import os; print(os.environ['PIP_KEYRING_PROVIDER'])"])

    assert result.stdout.strip() == "subprocess"


@pytest.mark.parametrize(
    ("variable", "value", "expected"),
    [
        pytest.param("PIP_KEYRING_PROVIDER", "import", "import", id="keyring-provider-preserved"),
        pytest.param("PIP_TARGET", "/some/custom/target", "unset", id="pip-target-removed"),
        pytest.param("PIP_USER", "1", "0", id="pip-user-disabled"),
    ],
)
def test_subprocess_env_seen_by_the_child(
    monkeypatch: pytest.MonkeyPatch, variable: str, value: str, expected: str
) -> None:
    monkeypatch.setenv(variable, value)

    result: Final = run_subprocess([
        sys.executable,
        "-c",
        f"import os; print(os.environ.get({variable!r}, 'unset'))",
    ])

    assert result.stdout.strip() == expected


def test_subprocess_pythonsafepath_set_for_python_commands() -> None:
    result: Final = run_subprocess([
        sys.executable,
        "-c",
        "import os, sys; sys.stdout.write(os.environ.get('PYTHONSAFEPATH', ''))",
    ])

    assert result.stdout == "1"


@pytest.mark.parametrize(
    ("capture_stderr", "stream_output"),
    [
        pytest.param(False, False, id="uncaptured"),
        pytest.param(True, True, id="streamed"),
    ],
)
def test_subprocess_holds_output_of_fan_out_task_waiting_its_turn(
    capfd: pytest.CaptureFixture[str], capture_stderr: bool, stream_output: bool
) -> None:
    second_done: Final[threading.Event] = threading.Event()

    def first() -> None:
        second_done.wait(timeout=5)
        sys.stderr.write("first ")
        sys.stderr.flush()

    def second() -> None:
        run_subprocess(
            [sys.executable, "-c", "import sys; sys.stderr.write('second')"],
            capture_stderr=capture_stderr,
            stream_output=stream_output,
        )
        second_done.set()

    fan_out([first, second], sequential=False)

    assert capfd.readouterr().err == "first second"


def test_subprocess_held_uncaptured_stderr_stays_unset() -> None:
    second_done: Final[threading.Event] = threading.Event()

    def second() -> str | None:
        stderr = run_subprocess([sys.executable, "-c", "import sys"], capture_stderr=False).stderr
        second_done.set()
        return stderr

    assert fan_out([lambda: second_done.wait(timeout=5), second], sequential=False) == [True, None]


@pytest.mark.parametrize("stream_output", [pytest.param(False, id="captured"), pytest.param(True, id="streamed")])
@pytest.mark.usefixtures("typed_input")
def test_subprocess_of_fan_out_task_waiting_its_turn_reads_no_input(stream_output: bool) -> None:
    second_done: Final[threading.Event] = threading.Event()

    def second() -> str:
        stdout = run_subprocess(
            [sys.executable, "-c", "import sys; print(repr(sys.stdin.read()))"], stream_output=stream_output
        ).stdout
        second_done.set()
        return stdout

    assert fan_out([lambda: second_done.wait(timeout=5), second], sequential=False) == [True, "''\n"]


@pytest.fixture
def typed_input() -> Iterator[None]:
    read_end, write_end = os.pipe()
    os.write(write_end, b"typed")
    os.close(write_end)
    saved: Final[int] = os.dup(0)
    os.dup2(read_end, 0)
    os.close(read_end)
    try:
        yield
    finally:
        os.dup2(saved, 0)
        os.close(saved)


def test_subprocess_streams_and_captures_output(capsys: pytest.CaptureFixture[str]) -> None:
    result: Final[subprocess.CompletedProcess[str]] = run_subprocess(
        [
            sys.executable,
            "-c",
            (
                "import sys; sys.stdout.buffer.write('stdøut 1\\rstdøut 2\\r'.encode()); sys.stdout.flush(); "
                "sys.stderr.buffer.write('stdërr 1\\rstdërr 2\\r\\n'.encode()); sys.stderr.flush()"
            ),
        ],
        stream_output=True,
    )

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (captured.out, captured.err, result.stdout, result.stderr) == (
        "stdøut 1\rstdøut 2\r",
        "stdërr 1\rstdërr 2\n",
        "stdøut 1\rstdøut 2\r",
        "stdërr 1\rstdërr 2\n",
    )


@pytest.mark.parametrize("stream_output", [pytest.param(False, id="captured"), pytest.param(True, id="streamed")])
def test_subprocess_captures_output_without_terminal_escapes(mocker: MockerFixture, stream_output: bool) -> None:
    mocker.patch("pipx.subprocess_runner.sys.stdout", StringIO())
    result: Final[subprocess.CompletedProcess[str]] = run_subprocess(
        [sys.executable, "-c", f"import sys; sys.stdout.write({_COLOURED_OUTPUT!r})"],
        capture_stderr=False,
        stream_output=stream_output,
    )

    assert result.stdout == "satisfy\n      Python>=3.12 link\n"


def test_subprocess_stream_keeps_terminal_escapes_on_screen(mocker: MockerFixture) -> None:
    destination: Final[StringIO] = StringIO()
    mocker.patch("pipx.subprocess_runner.sys.stdout", destination)
    run_subprocess(
        [sys.executable, "-c", f"import sys; sys.stdout.write({_COLOURED_OUTPUT!r})"],
        capture_stderr=False,
        stream_output=True,
    )

    assert destination.getvalue() == _COLOURED_OUTPUT


@pytest.mark.parametrize(
    ("stdout_is_a_terminal", "expected"),
    [
        pytest.param(True, "1 120", id="terminal"),
        pytest.param(False, "unset unset", id="pipe"),
    ],
)
def test_subprocess_stream_reports_the_terminal_to_the_child(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    stdout_is_a_terminal: bool,
    expected: str,
) -> None:
    monkeypatch.delenv("TTY_COMPATIBLE", raising=False)
    monkeypatch.delenv("COLUMNS", raising=False)
    mocker.patch("pipx.subprocess_runner.sys.stdout.isatty", return_value=stdout_is_a_terminal)
    mocker.patch("pipx.subprocess_runner.shutil.get_terminal_size", return_value=os.terminal_size((120, 40)))
    result: Final[subprocess.CompletedProcess[str]] = run_subprocess(
        [
            sys.executable,
            "-c",
            "import os; print(os.environ.get('TTY_COMPATIBLE', 'unset'), os.environ.get('COLUMNS', 'unset'))",
        ],
        stream_output=True,
    )

    assert result.stdout.strip() == expected


@pytest.mark.parametrize(
    ("destination_is_a_terminal", "expected"),
    [
        pytest.param(True, "True", id="hands-a-terminal", marks=SKIP_IF_WINDOWS),
        pytest.param(False, "False", id="leaves-a-pipe"),
    ],
)
def test_subprocess_stream_child_sees_a_terminal_only_behind_one(
    mocker: MockerFixture, destination_is_a_terminal: bool, expected: str
) -> None:
    destination: Final[StringIO] = StringIO()
    mocker.patch.object(destination, "isatty", return_value=destination_is_a_terminal)
    mocker.patch("pipx.subprocess_runner.sys.stdout", destination)
    result: Final[subprocess.CompletedProcess[str]] = run_subprocess(
        [sys.executable, "-c", "import sys; print(sys.stdout.isatty())"],
        capture_stderr=False,
        stream_output=True,
    )

    assert result.stdout.strip() == expected


def test_subprocess_stream_normalizes_split_crlf(mocker: MockerFixture) -> None:
    destination: Final[StringIO] = StringIO()
    mocker.patch("pipx.subprocess_runner.sys.stdout", destination)
    read_size: Final[int] = 8 * 1024
    result: Final[subprocess.CompletedProcess[str]] = run_subprocess(
        [
            sys.executable,
            "-c",
            f"import os, sys; os.write(sys.stdout.fileno(), b'x' * {read_size - 1} + b'\\r\\n')",
        ],
        capture_stderr=False,
        stream_output=True,
    )
    expected: Final[str] = "x" * (read_size - 1) + "\n"

    assert (destination.getvalue(), result.stdout) == (expected, expected)


@pytest.mark.parametrize(
    "statement",
    [
        pytest.param("print('stdout')", id="stdout"),
        pytest.param("print('stderr', file=sys.stderr)", id="stderr"),
    ],
)
def test_subprocess_stream_does_not_log_capture(
    caplog: pytest.LogCaptureFixture,
    statement: str,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="pipx.subprocess_runner"):
        run_subprocess(
            [sys.executable, "-c", f"import sys; {statement}"],
            stream_output=True,
        )

    assert [record.getMessage() for record in caplog.records if record.levelno == logging.DEBUG] == ["returncode: 0"]


def test_subprocess_stream_drains_before_output_error(mocker: MockerFixture) -> None:
    destination: Final[TextIOWrapper] = TextIOWrapper(BytesIO(), encoding="ascii")
    mocker.patch("pipx.subprocess_runner.sys.stdout", destination)

    with pytest.raises(UnicodeEncodeError):
        run_subprocess(
            [sys.executable, "-c", "print('ø' * 100_000)"],
            capture_stderr=False,
            stream_output=True,
        )


@pytest.mark.skipif(sys.platform != "darwin", reason="only macOS drops what a closing pseudo-terminal still queues")
@pytest.mark.usefixtures("terminal_stdout")
@pytest.mark.timeout(60)  # 300 process launches take about 30 s on a macOS CI runner
def test_subprocess_stream_keeps_output_of_a_child_that_exits_at_once() -> None:
    # the loss hit about 1 run in 75 on a CI macOS runner, so a few hundred runs catch it reliably
    outputs: Final[set[str]] = {
        run_subprocess([sys.executable, "-c", "print('payload')"], stream_output=True).stdout.strip()
        for _ in range(300)
    }

    assert outputs == {"payload"}


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("terminal_stdout")
def test_subprocess_stream_propagates_ctrl_c() -> None:
    # Ctrl-C on a terminal reaches the whole foreground process group: pipx and the child alike
    with pytest.raises(KeyboardInterrupt):
        run_subprocess(
            [
                sys.executable,
                "-c",
                "import os, signal; os.kill(os.getppid(), signal.SIGINT); os.kill(os.getpid(), signal.SIGINT)",
            ],
            stream_output=True,
        )


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("terminal_stdout")
def test_subprocess_stream_propagates_ctrl_c_while_readers_start(mocker: MockerFixture) -> None:
    submit: Final = ThreadPoolExecutor.submit

    def interrupted_second_reader(
        executor: ThreadPoolExecutor, fn: Callable[..., None], /, *args: object
    ) -> Future[None]:
        # Ctrl-C lands after the terminal's reader started but before the next one did, as seen on free-threaded CI
        if submitted:
            raise KeyboardInterrupt
        submitted.append(True)
        return submit(executor, fn, *args)

    submitted: Final[list[bool]] = []
    mocker.patch.object(ThreadPoolExecutor, "submit", autospec=True, side_effect=interrupted_second_reader)

    with pytest.raises(KeyboardInterrupt):
        run_subprocess([sys.executable, "-c", "import time; time.sleep(30)"], stream_output=True)


@pytest.mark.parametrize("stream_output", [pytest.param(False, id="captured"), pytest.param(True, id="streamed")])
def test_subprocess_replaces_undecodable_output(stream_output: bool) -> None:
    result: Final[subprocess.CompletedProcess[str]] = run_subprocess(
        [sys.executable, "-c", _UNDECODABLE_OUTPUT], capture_stderr=False, stream_output=stream_output
    )

    assert result.stdout == "\ufffd bad\nafter\n"


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("terminal_stdout")
def test_subprocess_stream_replaces_undecodable_terminal_output() -> None:
    result: Final[subprocess.CompletedProcess[str]] = run_subprocess(
        [sys.executable, "-c", _UNDECODABLE_OUTPUT], capture_stderr=False, stream_output=True
    )

    assert result.stdout == "\ufffd bad\nafter\n"


@SKIP_IF_WINDOWS
def test_subprocess_stream_stops_draining_a_failed_reader(mocker: MockerFixture) -> None:
    destination: Final[StringIO] = StringIO()
    mocker.patch.object(destination, "isatty", return_value=True)
    mocker.patch("pipx.subprocess_runner.sys.stdout", destination)
    destination.close()

    with pytest.raises(ValueError, match="closed file"):
        run_subprocess(
            # the pause leaves the second line unread after the first write kills the reader
            [
                sys.executable,
                "-c",
                "import os, time; os.write(1, b'first\\n'); time.sleep(0.2); os.write(1, b'second\\n')",
            ],
            capture_stderr=False,
            stream_output=True,
        )


@pytest.fixture
def terminal_stdout(mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TTY_COMPATIBLE", raising=False)
    monkeypatch.delenv("COLUMNS", raising=False)
    mocker.patch("pipx.subprocess_runner.sys.stdout.isatty", return_value=True)
    mocker.patch("pipx.subprocess_runner.shutil.get_terminal_size", return_value=os.terminal_size((120, 40)))


@pytest.mark.parametrize(
    ("site_dirs", "expected"),
    [
        pytest.param(["lib/python3.99/site-packages"], ["lib/python3.99/site-packages"], id="posix"),
        pytest.param(["lib/python3.99t/site-packages"], ["lib/python3.99t/site-packages"], id="free-threaded"),
        pytest.param(["Lib/site-packages"], ["Lib/site-packages"], id="windows"),
        pytest.param(
            ["lib/python3.99/site-packages", "lib64/python3.99/site-packages"],
            ["lib/python3.99/site-packages", "lib64/python3.99/site-packages"],
            id="separate-lib64",
        ),
    ],
)
def test_get_site_packages_reads_the_venv_layout(tmp_path: Path, site_dirs: list[str], expected: list[str]) -> None:
    for site_dir in site_dirs:
        (tmp_path / site_dir).mkdir(parents=True)

    # no interpreter exists at this path, so only the layout can answer
    assert get_site_packages(tmp_path / "bin" / "python") == [tmp_path / site_dir for site_dir in expected]


@SKIP_IF_WINDOWS
def test_get_site_packages_skips_a_lib64_linked_to_lib(tmp_path: Path) -> None:
    (purelib := tmp_path / "lib" / "python3.99" / "site-packages").mkdir(parents=True)
    (tmp_path / "lib64").symlink_to("lib")

    assert get_site_packages(tmp_path / "bin" / "python") == [purelib]


@SKIP_IF_WINDOWS
def test_get_site_packages_asks_the_interpreter_when_the_layout_is_ambiguous(tmp_path: Path) -> None:
    EnvBuilder(symlinks=True).create(tmp_path)
    (tmp_path / "lib" / "python3.0" / "site-packages").mkdir(parents=True)
    interpreter: Final[Path] = tmp_path / "bin" / "python"
    output: Final[list[str]] = subprocess.run(
        (
            str(interpreter),
            "-c",
            "import sysconfig; print(sysconfig.get_path('purelib')); print(sysconfig.get_path('platlib'))",
        ),
        capture_output=True,
        check=True,
        text=True,
    ).stdout.splitlines()
    purelib, platlib = (Path(path) for path in output)

    assert get_site_packages(interpreter) == (
        [purelib] if purelib.resolve() == platlib.resolve() else [purelib, platlib]
    )


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        pytest.param(
            ["pip", "--index-url", "https://alice:s3cr3t@host/simple"],
            "'pip --index-url https://****:****@host/simple' failed",
            id="password",
        ),
        pytest.param(
            ["pip", "--index-url", "https://alice:correct horse@host/simple"],
            "'pip --index-url https://****:****@host/simple' failed",
            id="space-in-password",
        ),
        pytest.param(
            ["pip", "--index-url", "https://host", "tool @ https://host/tool.whl"],
            "'pip --index-url https://host tool @ https://host/tool.whl' failed",
            id="no-credentials-across-arguments",
        ),
    ],
)
def test_subprocess_post_check_reports_failed_command_without_credentials(args: list[str], expected: str) -> None:
    with pytest.raises(PipxError) as error:
        subprocess_post_check(subprocess.CompletedProcess(args, 1, "", ""))

    assert error.value.raw_message == expected


@pytest.mark.parametrize("stream", [pytest.param("stdout", id="stdout"), pytest.param("stderr", id="stderr")])
def test_run_subprocess_masks_url_credentials_in_output(stream: str) -> None:
    url: Final[str] = "https://deploy:s3cr3ttok@host/team/tool"

    process: Final = run_subprocess([sys.executable, "-c", f"import sys; print({url!r}, file=sys.{stream})"])

    assert getattr(process, stream).strip() == redact_url_credentials(url)
