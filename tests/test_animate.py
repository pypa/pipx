import time

import pytest

import pipx.animate
from pipx.animate import (
    CLEAR_LINE,
    EMOJI_ANIMATION_FRAMES,
    EMOJI_FRAME_PERIOD,
    NONEMOJI_ANIMATION_FRAMES,
    NONEMOJI_FRAME_PERIOD,
)

# 40-char test_string counts columns e.g.: "0204060810 ... 363840"
TEST_STRING_40_CHAR = "".join([f"{x:02}" for x in range(2, 41, 2)])


def check_animate_output(
    capsys,
    test_string,
    frame_strings,
    frame_period,
    frames_to_test,
    extra_animate_time=0.4,
    extra_after_thread_time=0.1,
):
    # NOTE: extra_animate_time <= 0.3 failed on macos
    #       extra_after_thread_time <= 0.0 failed on macos
    expected_string = "".join(frame_strings)

    chars_to_test = 1 + len("".join(frame_strings[:frames_to_test]))

    with pipx.animate.animate(test_string, do_animation=True):
        time.sleep(frame_period * (frames_to_test - 1) + extra_animate_time)
    # Wait before capturing stderr to ensure animate thread is finished
    #   and to capture all its characters. If some are left over they can cause
    #   false fail in the next call of check_animate_output()
    time.sleep(extra_after_thread_time)
    captured = capsys.readouterr()

    print("check_animate_output() Test Debug Output:")
    if len(captured.err) < chars_to_test:
        print(
            "Not enough captured characters--Likely need to increase extra_animate_time"
        )
    if (
        captured.err[: len(frame_strings[0])]
        != expected_string[: len(frame_strings[0])]
    ):
        print("Error in first frame--Might need to increase extra_after_thread_time")
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
    "env_columns,expected_message",
    [
        (45, f"{TEST_STRING_40_CHAR:.{45-6}}..."),
        (46, f"{TEST_STRING_40_CHAR}"),
        (47, f"{TEST_STRING_40_CHAR}"),
    ],
)
def test_line_lengths_emoji(capsys, monkeypatch, env_columns, expected_message):
    # emoji_support and stderr_is_tty is set only at import animate.py
    # since we are already after that, we must override both here
    monkeypatch.setattr(pipx.animate, "stderr_is_tty", True)
    monkeypatch.setattr(pipx.animate, "emoji_support", True)

    frames_to_test = 4

    monkeypatch.setenv("COLUMNS", str(env_columns))

    frame_strings = [
        f"{CLEAR_LINE}\r{x} {expected_message[i]}" for x in EMOJI_ANIMATION_FRAMES
    ]
    check_animate_output(
        capsys, TEST_STRING_40_CHAR, frame_strings, EMOJI_FRAME_PERIOD, frames_to_test
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
