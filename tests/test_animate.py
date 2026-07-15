from __future__ import annotations

import threading
import time
from timeit import default_timer
from typing import TYPE_CHECKING, Final

import pytest

import pipx.animate
from pipx.animate import (
    CLEAR_LINE,
    EMOJI_ANIMATION_FRAMES,
    NONEMOJI_ANIMATION_FRAMES,
    hide_cursor,
    show_cursor,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_mock import MockerFixture

TEST_STRING_40_CHAR: Final[str] = "".join(f"{number:02}" for number in range(2, 41, 2))


def check_animate_output(
    capsys: pytest.CaptureFixture[str],
    test_string: str,
    frame_strings: list[str],
    frames_to_test: int,
) -> None:
    expected_string = "".join(frame_strings)
    chars_to_test = len("".join(frame_strings[:frames_to_test]))
    total_err = ""
    deadline = default_timer() + 5

    with pipx.animate.animate(test_string, do_animation=True):
        while default_timer() < deadline and len(total_err) < chars_to_test:
            total_err += capsys.readouterr().err
            time.sleep(0.01)

    total_err += capsys.readouterr().err
    assert total_err[:chars_to_test] == expected_string[:chars_to_test]


def test_delay_suppresses_output(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pipx.animate, "STDERR_IS_TTY", True)
    monkeypatch.setenv("COLUMNS", "80")

    test_string = "asdf"

    # The delay boundary requires elapsed time before checking for an early frame.
    with pipx.animate.animate(test_string, do_animation=True, delay=0.9):
        time.sleep(0.5)
    captured = capsys.readouterr()
    assert test_string not in captured.err


@pytest.mark.parametrize(
    ("cursor_control", "escape_sequence"),
    [(hide_cursor, "\033[?25l"), (show_cursor, "\033[?25h")],
    ids=["hide", "show"],
)
def test_cursor_control_uses_ansi(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    cursor_control: Callable[[], None],
    escape_sequence: str,
) -> None:
    monkeypatch.setattr(pipx.animate, "STDERR_IS_TTY", True)
    monkeypatch.setattr(pipx.animate, "WINDOWS", False)

    cursor_control()

    assert capsys.readouterr().err == escape_sequence


def test_animate_clears_after_thread_stops(monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    animation_clear_started = threading.Event()
    main_clear_started = threading.Event()
    writes: list[str] = []
    clear = f"\r{CLEAR_LINE}"

    def record_write(text: str) -> int:
        if text == clear:
            if threading.current_thread() is threading.main_thread():
                main_clear_started.set()
            else:
                animation_clear_started.set()
                main_clear_started.wait(timeout=1)
        writes.append(text)
        return len(text)

    stderr = mocker.MagicMock(write=mocker.Mock(side_effect=record_write))
    mocker.patch.object(pipx.animate.sys, "stderr", stderr)
    monkeypatch.setattr(pipx.animate, "STDERR_IS_TTY", True)
    monkeypatch.setattr(pipx.animate, "EMOJI_SUPPORT", True)
    monkeypatch.setenv("COLUMNS", "80")

    with pipx.animate.animate("message", do_animation=True):
        assert animation_clear_started.wait(timeout=1)

    assert writes[-1] == clear


@pytest.mark.parametrize(
    ("env_columns", "expected_frame_message"),
    [
        (45, f"{TEST_STRING_40_CHAR:.{45 - 6}}..."),
        (46, f"{TEST_STRING_40_CHAR}"),
        (47, f"{TEST_STRING_40_CHAR}"),
    ],
    ids=["truncated", "exact", "spare-column"],
)
def test_line_lengths_emoji(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    env_columns: int,
    expected_frame_message: str,
) -> None:
    monkeypatch.setattr(pipx.animate, "STDERR_IS_TTY", True)
    monkeypatch.setattr(pipx.animate, "EMOJI_SUPPORT", True)

    monkeypatch.setenv("COLUMNS", str(env_columns))

    frames_to_test = 4
    frame_strings = [f"\r{CLEAR_LINE}{x} {expected_frame_message}" for x in EMOJI_ANIMATION_FRAMES]
    check_animate_output(capsys, TEST_STRING_40_CHAR, frame_strings, frames_to_test)


@pytest.mark.parametrize(
    ("env_columns", "expected_frame_message"),
    [
        (43, f"{TEST_STRING_40_CHAR:.{43 - 4}}"),
        (44, f"{TEST_STRING_40_CHAR}"),
        (45, f"{TEST_STRING_40_CHAR}"),
    ],
    ids=["truncated", "exact", "spare-column"],
)
def test_line_lengths_no_emoji(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    env_columns: int,
    expected_frame_message: str,
) -> None:
    monkeypatch.setattr(pipx.animate, "STDERR_IS_TTY", True)
    monkeypatch.setattr(pipx.animate, "EMOJI_SUPPORT", False)

    monkeypatch.setenv("COLUMNS", str(env_columns))

    frames_to_test = 2
    frame_strings = [f"\r{CLEAR_LINE}{expected_frame_message}{x}" for x in NONEMOJI_ANIMATION_FRAMES]

    check_animate_output(
        capsys,
        TEST_STRING_40_CHAR,
        frame_strings,
        frames_to_test,
    )


@pytest.mark.parametrize(
    ("env_columns", "supports_tty"),
    [(0, True), (8, True), (16, True), (17, False)],
    ids=["zero-columns", "narrow-terminal", "threshold", "not-tty"],
)
def test_env_no_animate(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    env_columns: int,
    supports_tty: bool,
) -> None:
    monkeypatch.setattr(pipx.animate, "STDERR_IS_TTY", supports_tty)
    monkeypatch.setenv("COLUMNS", str(env_columns))

    expected_string = f"{TEST_STRING_40_CHAR}...\n"

    with pipx.animate.animate(TEST_STRING_40_CHAR, do_animation=True):
        pass

    captured = capsys.readouterr()

    assert not captured.out
    assert captured.err == expected_string
