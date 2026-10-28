from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from functools import partial
from io import BytesIO, StringIO, TextIOWrapper
from itertools import groupby
from pathlib import Path
from typing import TYPE_CHECKING, Final
from venv import EnvBuilder

import pytest

from helpers import skip_if_windows
from pipx import paths
from pipx.fanout import fan_out
from pipx.util import (
    exec_app,
    get_site_packages,
    redact_url_credentials,
    rmdir,
    run_subprocess,
    safe_unlink,
    subprocess_post_check,
    subprocess_post_check_handle_pip_error,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from _pytest.capture import CaptureResult
    from pytest_mock import MockerFixture


_UNDECODABLE_OUTPUT: Final[str] = "import os; os.write(1, b'\\xff bad\\n'); os.write(1, b'after\\n')"
_COLOURED_OUTPUT: Final[str] = "satisfy\n\x1b[31m      \x1b[0mPython>=3.12 \x1b]8;;https://x\x07link\x1b]8;;\x1b\\\n"


@pytest.mark.parametrize("windows", [pytest.param(False, id="posix"), pytest.param(True, id="windows")])
def test_exec_app_preserves_stream_encoding(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    windows: bool,
) -> None:
    monkeypatch.setattr("pipx.util.WINDOWS", windows)
    env = {"PYTHONIOENCODING": "cp850", "PYTHONLEGACYWINDOWSSTDIO": "cp850"}
    if windows:
        boundary = mocker.patch("pipx.util.subprocess.run", autospec=True, side_effect=RuntimeError)
    else:
        boundary = mocker.patch("pipx.util.os.execvpe", autospec=True, side_effect=RuntimeError)

    with pytest.raises(RuntimeError):
        exec_app(["python"], env)

    child_env = boundary.call_args.kwargs["env"] if windows else boundary.call_args.args[2]
    assert child_env["PYTHONIOENCODING"] == "cp850"
    assert child_env["PYTHONLEGACYWINDOWSSTDIO"] == "cp850"


def test_rmdir_without_safe_rm_is_non_fatal_for_locked_files(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    trash_dir = tmp_path / "trash"
    trash_dir.mkdir()
    (trash_dir / "locked.dll").write_text("locked")

    def fake_rmtree(path: Path, ignore_errors: bool = False) -> None:
        assert path == trash_dir
        if not ignore_errors:
            msg = "locked file"
            raise PermissionError(msg)

    monkeypatch.setattr("pipx.util.shutil.rmtree", fake_rmtree)

    with caplog.at_level(logging.WARNING, logger="pipx.util"):
        rmdir(trash_dir, safe_rm=False)

    assert trash_dir.is_dir()
    assert f"Failed to delete {trash_dir}. You may need to delete it manually." in caplog.text


def test_rmdir_with_safe_rm_is_non_fatal_when_move_fails(
    caplog: pytest.LogCaptureFixture,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    path = tmp_path / "locked"
    path.mkdir()
    mocker.patch("pipx.util.shutil.rmtree")
    mocker.patch.object(Path, "rename", side_effect=PermissionError("locked directory"))
    mocker.patch.object(type(paths.ctx), "trash", mocker.PropertyMock(return_value=tmp_path / "trash"))

    with caplog.at_level(logging.WARNING, logger="pipx.util"):
        rmdir(path)

    assert path.is_dir()
    assert f"Failed to move {path} to the trash" in caplog.text


def test_safe_unlink_handles_existing_trash_directory(mocker: MockerFixture, tmp_path: Path) -> None:
    file = tmp_path / "locked"
    file.write_text("content")
    trash_dir = tmp_path / "trash"
    trash_dir.mkdir()
    is_dir = Path.is_dir
    stale = True

    def stale_is_dir(path: Path) -> bool:
        nonlocal stale
        if path == trash_dir and stale:
            stale = False
            return False
        return is_dir(path)

    mocker.patch.object(type(paths.ctx), "trash", mocker.PropertyMock(return_value=trash_dir))
    mocker.patch.object(Path, "is_dir", stale_is_dir)
    mocker.patch.object(Path, "unlink", side_effect=PermissionError("locked file"))

    safe_unlink(file)

    assert not file.exists()
    assert [path.read_text() for path in trash_dir.iterdir()] == ["content"]


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        pytest.param(None, "subprocess", id="defaults_to_subprocess"),
        pytest.param("import", "import", id="preserves_explicit"),
    ],
)
def test_subprocess_keyring_provider(monkeypatch: pytest.MonkeyPatch, env_value: str | None, expected: str) -> None:
    if env_value is not None:
        monkeypatch.setenv("PIP_KEYRING_PROVIDER", env_value)
    else:
        monkeypatch.delenv("PIP_KEYRING_PROVIDER", raising=False)

    result = run_subprocess([sys.executable, "-c", "import os; print(os.environ['PIP_KEYRING_PROVIDER'])"])

    assert result.stdout.strip() == expected


def test_subprocess_pythonsafepath_set_for_python_commands() -> None:
    """Test that PYTHONSAFEPATH is set for Python subprocess calls to prevent CWD shadowing (issue #1575)."""
    result = run_subprocess([
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
    mocker.patch("pipx.util.sys.stdout", StringIO())
    result: Final[subprocess.CompletedProcess[str]] = run_subprocess(
        [sys.executable, "-c", f"import sys; sys.stdout.write({_COLOURED_OUTPUT!r})"],
        capture_stderr=False,
        stream_output=stream_output,
    )

    assert result.stdout == "satisfy\n      Python>=3.12 link\n"


def test_subprocess_stream_keeps_terminal_escapes_on_screen(mocker: MockerFixture) -> None:
    destination: Final[StringIO] = StringIO()
    mocker.patch("pipx.util.sys.stdout", destination)
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
    mocker.patch("pipx.util.sys.stdout.isatty", return_value=stdout_is_a_terminal)
    mocker.patch("pipx.util.shutil.get_terminal_size", return_value=os.terminal_size((120, 40)))
    result: Final[subprocess.CompletedProcess[str]] = run_subprocess(
        [
            sys.executable,
            "-c",
            "import os; print(os.environ.get('TTY_COMPATIBLE', 'unset'), os.environ.get('COLUMNS', 'unset'))",
        ],
        stream_output=True,
    )

    assert result.stdout.strip() == expected


@skip_if_windows
def test_subprocess_stream_hands_a_terminal_to_the_child(mocker: MockerFixture) -> None:
    destination: Final[StringIO] = StringIO()
    mocker.patch.object(destination, "isatty", return_value=True)
    mocker.patch("pipx.util.sys.stdout", destination)
    result: Final[subprocess.CompletedProcess[str]] = run_subprocess(
        [sys.executable, "-c", "import sys; print(sys.stdout.isatty())"],
        capture_stderr=False,
        stream_output=True,
    )

    assert result.stdout.strip() == "True"


def test_subprocess_stream_leaves_a_pipe_to_the_child_without_a_terminal(mocker: MockerFixture) -> None:
    destination: Final[StringIO] = StringIO()
    mocker.patch("pipx.util.sys.stdout", destination)
    result: Final[subprocess.CompletedProcess[str]] = run_subprocess(
        [sys.executable, "-c", "import sys; print(sys.stdout.isatty())"],
        capture_stderr=False,
        stream_output=True,
    )

    assert result.stdout.strip() == "False"


def test_subprocess_stream_normalizes_split_crlf(mocker: MockerFixture) -> None:
    destination: Final[StringIO] = StringIO()
    mocker.patch("pipx.util.sys.stdout", destination)
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
    with caplog.at_level(logging.DEBUG, logger="pipx.util"):
        run_subprocess(
            [sys.executable, "-c", f"import sys; {statement}"],
            stream_output=True,
        )

    assert [record.getMessage() for record in caplog.records if record.levelno == logging.DEBUG] == ["returncode: 0"]


def test_subprocess_stream_drains_before_output_error(mocker: MockerFixture) -> None:
    destination: Final[TextIOWrapper] = TextIOWrapper(BytesIO(), encoding="ascii")
    mocker.patch("pipx.util.sys.stdout", destination)

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


@skip_if_windows
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


@skip_if_windows
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


@skip_if_windows
@pytest.mark.usefixtures("terminal_stdout")
def test_subprocess_stream_replaces_undecodable_terminal_output() -> None:
    result: Final[subprocess.CompletedProcess[str]] = run_subprocess(
        [sys.executable, "-c", _UNDECODABLE_OUTPUT], capture_stderr=False, stream_output=True
    )

    assert result.stdout == "\ufffd bad\nafter\n"


@skip_if_windows
def test_subprocess_stream_stops_draining_a_failed_reader(mocker: MockerFixture) -> None:
    destination: Final[StringIO] = StringIO()
    mocker.patch.object(destination, "isatty", return_value=True)
    mocker.patch("pipx.util.sys.stdout", destination)
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
    mocker.patch("pipx.util.sys.stdout.isatty", return_value=True)
    mocker.patch("pipx.util.shutil.get_terminal_size", return_value=os.terminal_size((120, 40)))


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


@skip_if_windows
def test_get_site_packages_skips_a_lib64_linked_to_lib(tmp_path: Path) -> None:
    (purelib := tmp_path / "lib" / "python3.99" / "site-packages").mkdir(parents=True)
    (tmp_path / "lib64").symlink_to("lib")

    assert get_site_packages(tmp_path / "bin" / "python") == [purelib]


@skip_if_windows
def test_get_site_packages_asks_the_interpreter_when_the_layout_is_ambiguous(tmp_path: Path) -> None:
    EnvBuilder(symlinks=True).create(tmp_path)
    (tmp_path / "lib" / "python3.0" / "site-packages").mkdir(parents=True)
    interpreter = tmp_path / "bin" / "python"
    output = subprocess.run(
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


def test_pip_error_logs_of_concurrent_failures_stay_whole(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths.ctx, "log_file", tmp_path / "cmd.log")
    tags: Final[str] = "ABCDEFGH"

    def fail(tag: str) -> None:
        output: Final[str] = f"{tag * 79}\n" * 2000
        subprocess_post_check_handle_pip_error(subprocess.CompletedProcess([], 1, output, output))

    fan_out([partial(fail, tag) for tag in tags], sequential=False)

    lines: Final[list[str]] = (tmp_path / "cmd_pip_errors.log").read_text(encoding="utf-8").splitlines()
    blocks: Final[list[str]] = [tag for tag, _ in groupby(line[0] for line in lines if line[:1] in set(tags))]
    assert sorted(blocks) == sorted(tags)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(
            "pip --index-url https://alice:s3cr3t@host/simple",
            "pip --index-url https://alice:****@host/simple",
            id="user-and-password",
        ),
        pytest.param("pip git+https://t0ken@host/repo.git", "pip git+https://****@host/repo.git", id="token"),
        pytest.param("pip foo @ https://host/a@b.whl", "pip foo @ https://host/a@b.whl", id="no-credentials"),
        pytest.param("https://host?x=a@b", "https://host?x=a@b", id="at-in-query"),
        pytest.param("https://host#egg=x@1", "https://host#egg=x@1", id="at-in-fragment"),
        pytest.param("https://u:p@w@host/x", "https://u:****@host/x", id="unescaped-at-in-password"),
        pytest.param("git+ssh://git@github.com/a/b", "git+ssh://****@github.com/a/b", id="bare-user"),
        pytest.param(
            "https://alice:correct horse@host/simple", "https://alice:****@host/simple", id="space-in-password"
        ),
        pytest.param(
            "https://alice:correct\thorse@host/simple", "https://alice:****@host/simple", id="tab-in-password"
        ),
        pytest.param(
            "--index-url https://a:b@one/s --extra-index-url https://c@two/s",
            "--index-url https://a:****@one/s --extra-index-url https://****@two/s",
            id="two-urls",
        ),
    ],
)
def test_redact_url_credentials_masks_userinfo(text: str, expected: str) -> None:
    assert redact_url_credentials(text) == expected


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        pytest.param(
            ["pip", "--index-url", "https://alice:s3cr3t@host/simple"],
            "'pip --index-url https://alice:****@host/simple' failed",
            id="password",
        ),
        pytest.param(
            ["pip", "--index-url", "https://alice:correct horse@host/simple"],
            "'pip --index-url https://alice:****@host/simple' failed",
            id="space-in-password",
        ),
        pytest.param(
            ["pip", "--index-url", "https://host", "tool @ https://host/tool.whl"],
            "'pip --index-url https://host tool @ https://host/tool.whl' failed",
            id="no-credentials-across-arguments",
        ),
    ],
)
def test_subprocess_post_check_logs_failed_command_without_credentials(
    caplog: pytest.LogCaptureFixture, args: list[str], expected: str
) -> None:
    with caplog.at_level(logging.INFO, logger="pipx.util"):
        subprocess_post_check(subprocess.CompletedProcess(args, 1, "", ""), raise_error=False)

    assert caplog.messages == [expected]
