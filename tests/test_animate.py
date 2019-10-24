#!/usr/bin/env python3
import time

import pipx.animate


HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
CLEAR_LINE = "\033[K"


def check_animate_output(
    capsys, test_string, frame_strings, frame_period, frames_to_test
):
    expected_string = f"{HIDE_CURSOR}" + "".join(frame_strings)

    chars_to_test = 1 + len("".join(frame_strings[:frames_to_test]))

    with pipx.animate.animate(test_string, do_animation=True):
        time.sleep(frame_period * (frames_to_test - 1) + 0.1)
    captured = capsys.readouterr()

    # print for debug help if fail
    print("expected_string:")
    print(repr(expected_string[:chars_to_test]))
    print("capsys sterr:")
    print(repr(captured.err[:chars_to_test]))

    assert captured.err[:chars_to_test] == expected_string[:chars_to_test]


def test_line_lengths_emoji(capsys, monkeypatch):
    # emoji_support and stderr_is_tty is set only at import animate.py
    # since we are already after that, we must override both here
    pipx.animate.stderr_is_tty = True
    pipx.animate.emoji_support = True

    frames_to_test = 4
    # matches animate.py
    frame_period = 0.1

    # 40-char test_string counts columns e.g.: "0204060810 ... 363840"
    test_string = "".join([f"{x:02}" for x in range(2, 41, 2)])

    columns_to_test = [45, 46, 47]
    expected_message = [f"{test_string:.{45-6}}...", f"{test_string}", f"{test_string}"]

    for i, columns in enumerate(columns_to_test):
        monkeypatch.setenv("COLUMNS", str(columns))

        frame_strings = [
            f"{CLEAR_LINE}\r{x} {expected_message[i]}"
            for x in ["⣷", "⣯", "⣟", "⡿", "⢿", "⣻", "⣽", "⣾"]
        ]
        check_animate_output(
            capsys, test_string, frame_strings, frame_period, frames_to_test
        )

    # set back to test-normal
    pipx.animate.stderr_is_tty = False
    pipx.animate.emoji_support = True


def test_line_lengths_no_emoji(capsys, monkeypatch):
    # emoji_support and stderr_is_tty is set only at import animate.py
    # since we are already after that, we must override both here
    pipx.animate.stderr_is_tty = True
    pipx.animate.emoji_support = False

    frames_to_test = 2
    # matches animate.py
    frame_period = 1

    # 40-char test_string counts columns e.g.: "0204060810 ... 363840"
    test_string = "".join([f"{x:02}" for x in range(2, 41, 2)])

    columns_to_test = [43, 44, 45]
    expected_message = [f"{test_string:.{43-4}}", f"{test_string}", f"{test_string}"]

    for i, columns in enumerate(columns_to_test):
        monkeypatch.setenv("COLUMNS", str(columns))

        frame_strings = [
            f"{CLEAR_LINE}\r{expected_message[i]}{x}" for x in ["", ".", "..", "..."]
        ]

        check_animate_output(
            capsys, test_string, frame_strings, frame_period, frames_to_test
        )

    # set back to test-normal
    pipx.animate.stderr_is_tty = False
    pipx.animate.emoji_support = True
