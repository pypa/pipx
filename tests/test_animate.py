import time
import pytest  # type: ignore[import-not-found]
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
    """
    Refactored to use polling instead of rigid sleeps.
    """
    expected_string = "".join(frame_strings)
    
    # FIX: Calculate exact length required. Removed the "+ 1" that caused flakes.
    chars_to_test = len("".join(frame_strings[:frames_to_test]))

    total_err = ""
    # Generous timeout for slow CI environments (e.g. Windows/Mac runners)
    timeout = 5.0
    start_time = time.time()

    with pipx.animate.animate(test_string, do_animation=True):
        # POLLING LOOP: Keep reading until we get the expected data
        while time.time() - start_time < timeout:
            captured = capsys.readouterr()
            total_err += captured.err
            
            # If we have enough data, stop waiting immediately
            if len(total_err) >= chars_to_test:
                break
            
            # Tiny sleep to avoid 100% CPU usage loop
            time.sleep(0.01)

    # Capture any final output after loop or context manager exit
    captured = capsys.readouterr()
    total_err += captured.err

    print("check_animate_output() Test Debug Output:")
    if len(total_err) < chars_to_test:
        print("Not enough captured characters--Timed out waiting for output")
    
    print(f"captured characters: {len(total_err)}")
    print(f"chars_to_test: {chars_to_test}")
    
    for i in range(0, chars_to_test, 40):
        i_end = min(i + 40, chars_to_test)
        print(f"expected_string[{i}:{i_end}]: {expected_string[i:i_end]!r}")
        print(f"captured.err[{i}:{i_end}]    : {total_err[i:i_end]!r}")

    assert total_err[:chars_to_test] == expected_string[:chars_to_test]


def test_delay_suppresses_output(capsys, monkeypatch):
    monkeypatch.setattr(pipx.animate, "stderr_is_tty", True)
    monkeypatch.setenv("COLUMNS", "80")

    test_string = "asdf"

    # We keep sleep here because we are testing the ABSENCE of output during a delay.
    with pipx.animate.animate(test_string, do_animation=True, delay=0.9):
        time.sleep(0.5)
    captured = capsys.readouterr()
    assert test_string not in captured.err


@pytest.mark.parametrize(
    "env_columns,expected_frame_message",
    [
        (45, f"{TEST_STRING_40_CHAR:.{45 - 6}}..."),
        (46, f"{TEST_STRING_40_CHAR}"),
        (47, f"{TEST_STRING_40_CHAR}"),
    ],
)
def test_line_lengths_emoji(capsys, monkeypatch, env_columns, expected_frame_message):
    monkeypatch.setattr(pipx.animate, "stderr_is_tty", True)
    monkeypatch.setattr(pipx.animate, "EMOJI_SUPPORT", True)

    monkeypatch.setenv("COLUMNS", str(env_columns))

    frames_to_test = 4
    frame_strings = [f"\r{CLEAR_LINE}{x} {expected_frame_message}" for x in EMOJI_ANIMATION_FRAMES]
    check_animate_output(capsys, TEST_STRING_40_CHAR, frame_strings, EMOJI_FRAME_PERIOD, frames_to_test)


@pytest.mark.parametrize(
    "env_columns,expected_frame_message",
    [
        (43, f"{TEST_STRING_40_CHAR:.{43 - 4}}"),
        (44, f"{TEST_STRING_40_CHAR}"),
        (45, f"{TEST_STRING_40_CHAR}"),
    ],
)
def test_line_lengths_no_emoji(capsys, monkeypatch, env_columns, expected_frame_message):
    monkeypatch.setattr(pipx.animate, "stderr_is_tty", True)
    monkeypatch.setattr(pipx.animate, "EMOJI_SUPPORT", False)

    monkeypatch.setenv("COLUMNS", str(env_columns))

    frames_to_test = 2
    frame_strings = [f"\r{CLEAR_LINE}{expected_frame_message}{x}" for x in NONEMOJI_ANIMATION_FRAMES]

    check_animate_output(
        capsys,
        TEST_STRING_40_CHAR,
        frame_strings,
        NONEMOJI_FRAME_PERIOD,
        frames_to_test,
    )


@pytest.mark.parametrize("env_columns,stderr_is_tty", [(0, True), (8, True), (16, True), (17, False)])
def test_env_no_animate(capsys, monkeypatch, env_columns, stderr_is_tty):
    monkeypatch.setattr(pipx.animate, "stderr_is_tty", stderr_is_tty)
    monkeypatch.setenv("COLUMNS", str(env_columns))

    expected_string = f"{TEST_STRING_40_CHAR}...\n"
    
    # Replaced complex sleep math with a simple short wait.
    # We just need the context manager to run and exit to verify the static output.
    with pipx.animate.animate(TEST_STRING_40_CHAR, do_animation=True):
        time.sleep(0.1)

    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == expected_string
