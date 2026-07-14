from __future__ import annotations

import logging
import os
import sys
from io import BytesIO, StringIO, TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from helpers import skip_if_windows
from pipx import paths
from pipx.util import exec_app, rmdir, run_subprocess, safe_unlink

if TYPE_CHECKING:
    import subprocess

    from _pytest.capture import CaptureResult
    from pytest_mock import MockerFixture


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
            raise PermissionError("locked file")

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
    result = run_subprocess(
        [sys.executable, "-c", "import os, sys; sys.stdout.write(os.environ.get('PYTHONSAFEPATH', ''))"]
    )

    assert result.stdout == "1"


def test_subprocess_streams_and_captures_output(capsys: pytest.CaptureFixture[str]) -> None:
    result: Final[subprocess.CompletedProcess[str]] = run_subprocess(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write('stdøut 1\\rstdøut 2\\r'.encode()); sys.stdout.flush(); "
            "sys.stderr.buffer.write('stdërr 1\\rstdërr 2\\r\\n'.encode()); sys.stderr.flush()",
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
