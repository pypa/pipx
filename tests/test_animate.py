import time

import pytest  # type: ignore

import pipx.animate
from pipx.animate import (
    CLEAR_LINE,
    EMOJI_ANIMATION_FRAMES,
    NONEMOJI_ANIMATION_FRAMES,
    EMOJI_FRAME_PERIOD,
    NONEMOJI_FRAME_PERIOD,
)


def check_animate_output(
    capsys,
    test_string,
    frame_strings,
    frame_period,
    frames_to_test,
    extra_animate_time=0.5,
    extra_wait_time=0.5,
):
    # NOTE: extra_animate_time <= 0.3 failed on macos
    #       extra_wait_time <= 0.0 failed on macos
    expected_string = "".join(frame_strings)

    chars_to_test = 1 + len("".join(frame_strings[:frames_to_test]))

    with pipx.animate.animate(test_string, do_animation=True):
        time.sleep(frame_period * (frames_to_test - 1) + extra_animate_time)
    # Wait 0.5s before capturing stderr to ensure animate thread is finished
    #   and to capture all its characters. If some are left over they can cause
    #   false fail in the next call of check_animate_output()
    time.sleep(extra_wait_time)
    captured = capsys.readouterr()

    if len(captured.err) < chars_to_test:
        print(
            "Not enough captured characters--Likely need to increase extra_animate_time"
        )
    print("check_animate_output() Test Debug Output:")
    print(f"captured characters: {len(captured.err)}")
    print(f"chars_to_test: {chars_to_test}")
    for i in range(0, chars_to_test, 40):
        i_end = min(i + 40, chars_to_test)
        print(f"expected_string[{i}:{i_end}]: {repr(expected_string[i:i_end])}")
        print(f"captured.err[{i}:{i_end}]   : {repr(captured.err[i:i_end])}")

    assert captured.err[:chars_to_test] == expected_string[:chars_to_test]


def test_delay_suppresses_output(capsys, monkeypatch):
    monkeypatch.setattr(pipx.animate, "stderr_is_tty", True)

    test_string = "asdf"

    with pipx.animate.animate(test_string, do_animation=True, delay=0.9):
        time.sleep(0.5)
    captured = capsys.readouterr()
    assert test_string not in captured.err


@pytest.mark.parametrize(
    "extra_animate_time,extra_wait_time",
    [
        (0.4, 0.1),
        (0.4, 0.2),
        (0.4, 0.3),
        (0.4, 0.4),
        (0.4, 0.5),
        (0.5, 0.1),
        (0.5, 0.2),
        (0.5, 0.3),
        (0.5, 0.4),
        (0.5, 0.5),
    ],
)
def test_line_lengths_emoji(capsys, monkeypatch, extra_animate_time, extra_wait_time):
    # emoji_support and stderr_is_tty is set only at import animate.py
    # since we are already after that, we must override both here
    monkeypatch.setattr(pipx.animate, "stderr_is_tty", True)
    monkeypatch.setattr(pipx.animate, "emoji_support", True)

    frames_to_test = 4

    # 40-char test_string counts columns e.g.: "0204060810 ... 363840"
    test_string = "".join([f"{x:02}" for x in range(2, 41, 2)])

    columns_to_test = [45, 46, 47]
    expected_message = [f"{test_string:.{45-6}}...", f"{test_string}", f"{test_string}"]

    for i, columns in enumerate(columns_to_test):
        monkeypatch.setenv("COLUMNS", str(columns))

        frame_strings = [
            f"{CLEAR_LINE}\r{x} {expected_message[i]}" for x in EMOJI_ANIMATION_FRAMES
        ]
        check_animate_output(
            capsys,
            test_string,
            frame_strings,
            EMOJI_FRAME_PERIOD,
            frames_to_test,
            extra_animate_time,
            extra_wait_time,
        )


def test_line_lengths_no_emoji(capsys, monkeypatch):
    # emoji_support and stderr_is_tty is set only at import animate.py
    # since we are already after that, we must override both here
    monkeypatch.setattr(pipx.animate, "stderr_is_tty", True)
    monkeypatch.setattr(pipx.animate, "emoji_support", False)

    frames_to_test = 2

    # 40-char test_string counts columns e.g.: "0204060810 ... 363840"
    test_string = "".join([f"{x:02}" for x in range(2, 41, 2)])

    columns_to_test = [43, 44, 45]
    expected_message = [f"{test_string:.{43-4}}", f"{test_string}", f"{test_string}"]

    for i, columns in enumerate(columns_to_test):
        monkeypatch.setenv("COLUMNS", str(columns))

        frame_strings = [
            f"{CLEAR_LINE}\r{expected_message[i]}{x}" for x in NONEMOJI_ANIMATION_FRAMES
        ]

        check_animate_output(
            capsys, test_string, frame_strings, NONEMOJI_FRAME_PERIOD, frames_to_test
        )
