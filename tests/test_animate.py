from __future__ import annotations

import io
import sys
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
from pipx.fanout import fan_out

if TYPE_CHECKING:
    from collections.abc import Callable

    from _pytest.capture import CaptureResult
    from pytest_mock import MockerFixture

_TEST_STRING_40_CHAR: Final[str] = "".join(f"{number:02}" for number in range(2, 41, 2))


def test_delay_suppresses_output(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pipx.animate, "STDERR_IS_TTY", True)
    monkeypatch.setenv("COLUMNS", "80")

    # stays inside the 0.9 s delay, so no frame may appear yet
    with pipx.animate.animate("asdf", do_animation=True, delay=0.9):
        time.sleep(0.5)

    assert "asdf" not in capsys.readouterr().err


@pytest.mark.parametrize(
    ("cursor_control", "escape_sequence"),
    [pytest.param(hide_cursor, "\033[?25l", id="hide"), pytest.param(show_cursor, "\033[?25h", id="show")],
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
    animation_clear_started: Final[threading.Event] = threading.Event()
    main_clear_started: Final[threading.Event] = threading.Event()
    writes: Final[list[str]] = []
    clear: Final[str] = f"\r{CLEAR_LINE}"

    def record_write(text: str) -> int:
        if text == clear:
            if threading.current_thread() is threading.main_thread():
                main_clear_started.set()
            else:
                animation_clear_started.set()
                main_clear_started.wait(timeout=1)
        writes.append(text)
        return len(text)

    mocker.patch.object(pipx.animate.sys, "stderr", mocker.MagicMock(write=mocker.Mock(side_effect=record_write)))
    monkeypatch.setattr(pipx.animate, "STDERR_IS_TTY", True)
    monkeypatch.setattr(pipx.animate, "EMOJI_SUPPORT", True)
    monkeypatch.setenv("COLUMNS", "80")

    with pipx.animate.animate("message", do_animation=True):
        assert animation_clear_started.wait(timeout=1)

    assert writes[-1] == clear


@pytest.mark.parametrize(
    ("env_columns", "expected_frame_message"),
    [
        pytest.param(45, f"{_TEST_STRING_40_CHAR:.{45 - 6}}...", id="truncated"),
        pytest.param(46, _TEST_STRING_40_CHAR, id="exact"),
        pytest.param(47, _TEST_STRING_40_CHAR, id="spare-column"),
    ],
)
def test_line_lengths_emoji(
    monkeypatch: pytest.MonkeyPatch,
    check_animate_output: Callable[[list[str], int], None],
    env_columns: int,
    expected_frame_message: str,
) -> None:
    monkeypatch.setattr(pipx.animate, "STDERR_IS_TTY", True)
    monkeypatch.setattr(pipx.animate, "EMOJI_SUPPORT", True)
    monkeypatch.setenv("COLUMNS", str(env_columns))

    check_animate_output([f"\r{CLEAR_LINE}{x} {expected_frame_message}" for x in EMOJI_ANIMATION_FRAMES], 4)


@pytest.fixture
def check_animate_output(monkeypatch: pytest.MonkeyPatch) -> Callable[[list[str], int], None]:
    def check(frame_strings: list[str], frames_to_test: int) -> None:
        # draining capsys while the animation thread writes loses a frame written between the read and the truncation
        stderr: Final[io.StringIO] = io.StringIO()
        monkeypatch.setattr(sys, "stderr", stderr)
        chars_to_test: Final[int] = len("".join(frame_strings[:frames_to_test]))
        deadline: Final[float] = default_timer() + 5

        with pipx.animate.animate(_TEST_STRING_40_CHAR, do_animation=True):
            while default_timer() < deadline and len(stderr.getvalue()) < chars_to_test:
                time.sleep(0.01)

        assert stderr.getvalue()[:chars_to_test] == "".join(frame_strings)[:chars_to_test]

    return check


@pytest.mark.parametrize(
    ("env_columns", "expected_frame_message"),
    [
        pytest.param(43, f"{_TEST_STRING_40_CHAR:.{43 - 4}}", id="truncated"),
        pytest.param(44, _TEST_STRING_40_CHAR, id="exact"),
        pytest.param(45, _TEST_STRING_40_CHAR, id="spare-column"),
    ],
)
def test_line_lengths_no_emoji(
    monkeypatch: pytest.MonkeyPatch,
    check_animate_output: Callable[[list[str], int], None],
    env_columns: int,
    expected_frame_message: str,
) -> None:
    monkeypatch.setattr(pipx.animate, "STDERR_IS_TTY", True)
    monkeypatch.setattr(pipx.animate, "EMOJI_SUPPORT", False)
    monkeypatch.setenv("COLUMNS", str(env_columns))

    check_animate_output([f"\r{CLEAR_LINE}{expected_frame_message}{x}" for x in NONEMOJI_ANIMATION_FRAMES], 2)


@pytest.mark.parametrize(
    ("env_columns", "supports_tty"),
    [
        pytest.param(0, True, id="zero-columns"),
        pytest.param(8, True, id="narrow-terminal"),
        pytest.param(16, True, id="threshold"),
        pytest.param(17, False, id="not-tty"),
    ],
)
def test_env_no_animate(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    env_columns: int,
    supports_tty: bool,
) -> None:
    monkeypatch.setattr(pipx.animate, "STDERR_IS_TTY", supports_tty)
    monkeypatch.setenv("COLUMNS", str(env_columns))

    with pipx.animate.animate(_TEST_STRING_40_CHAR, do_animation=True):
        pass

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (captured.out, captured.err) == ("", f"{_TEST_STRING_40_CHAR}...\n")


def test_animate_skips_spinner_of_task_waiting_its_turn(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pipx.animate, "STDERR_IS_TTY", True)
    monkeypatch.setenv("COLUMNS", "80")
    second_done: Final[threading.Event] = threading.Event()

    def second() -> None:
        with pipx.animate.animate("waiting its turn", do_animation=True):
            time.sleep(0.3)
        second_done.set()

    fan_out([lambda: second_done.wait(timeout=5), second], sequential=False)

    assert "waiting its turn" not in capsys.readouterr().err


def test_animate_spins_for_task_whose_turn_it_is(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pipx.animate, "STDERR_IS_TTY", True)
    monkeypatch.setenv("COLUMNS", "80")

    def first() -> None:
        with pipx.animate.animate("its turn", do_animation=True):
            time.sleep(0.3)

    fan_out([first, lambda: None], sequential=False)

    assert "its turn" in capsys.readouterr().err
