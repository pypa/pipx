import shutil
import sys
from contextlib import contextmanager
from threading import Event, Thread
from typing import Generator, List

from pipx.constants import WINDOWS
from pipx.emojis import EMOJI_SUPPORT

stderr_is_tty = sys.stderr.isatty()

CLEAR_LINE = "\033[K"
EMOJI_ANIMATION_FRAMES = ["⣷", "⣯", "⣟", "⡿", "⢿", "⣻", "⣽", "⣾"]
NONEMOJI_ANIMATION_FRAMES = ["", ".", "..", "..."]
EMOJI_FRAME_PERIOD = 0.1
NONEMOJI_FRAME_PERIOD = 1
MINIMUM_COLS_ALLOW_ANIMATION = 16


if WINDOWS:
    import ctypes

    class _CursorInfo(ctypes.Structure):
        _fields_ = (("size", ctypes.c_int), ("visible", ctypes.c_byte))


def _env_supports_animation() -> bool:
    (term_cols, _) = shutil.get_terminal_size(fallback=(0, 0))
    return stderr_is_tty and term_cols > MINIMUM_COLS_ALLOW_ANIMATION


@contextmanager
def animate(message: str, do_animation: bool, *, delay: float = 0) -> Generator[None, None, None]:
    if not do_animation or not _env_supports_animation():
        # No animation, just a single print of message
        sys.stderr.write(f"{message}...\n")
        yield
        return

    event = Event()

    if EMOJI_SUPPORT:
        animate_at_beginning_of_line = True
        symbols = EMOJI_ANIMATION_FRAMES
        period = EMOJI_FRAME_PERIOD
    else:
        animate_at_beginning_of_line = False
        symbols = NONEMOJI_ANIMATION_FRAMES
        period = NONEMOJI_FRAME_PERIOD

    thread_kwargs = {
        "message": message,
        "event": event,
        "symbols": symbols,
        "delay": delay,
        "period": period,
        "animate_at_beginning_of_line": animate_at_beginning_of_line,
    }

    t = Thread(target=print_animation, kwargs=thread_kwargs)
    t.start()

    try:
        yield
    finally:
        event.set()
        clear_line()


def print_animation(
    *,
    message: str,
    event: Event,
    symbols: List[str],
    delay: float,
    period: float,
    animate_at_beginning_of_line: bool,
) -> None:
    (term_cols, _) = shutil.get_terminal_size(fallback=(9999, 24))
    event.wait(delay)
    while not event.wait(0):
        for s in symbols:
            if animate_at_beginning_of_line:
                max_message_len = term_cols - len(f"{s} ... ")
                cur_line = f"{s} {message:.{max_message_len}}"
                if len(message) > max_message_len:
                    cur_line += "..."
            else:
                max_message_len = term_cols - len("... ")
                cur_line = f"{message:.{max_message_len}}{s}"

            clear_line()
            sys.stderr.write(cur_line)
            sys.stderr.flush()
            if event.wait(period):
                break


# for Windows pre-ANSI-terminal-support (before Windows 10 TH2 (v1511))
# https://stackoverflow.com/a/10455937
def win_cursor(visible: bool) -> None:
    if sys.platform != "win32":  # hello mypy
        return
    ci = _CursorInfo()
    handle = ctypes.windll.kernel32.GetStdHandle(-11)
    ctypes.windll.kernel32.GetConsoleCursorInfo(handle, ctypes.byref(ci))
    ci.visible = visible
    ctypes.windll.kernel32.SetConsoleCursorInfo(handle, ctypes.byref(ci))


def hide_cursor() -> None:
    if stderr_is_tty:
        if WINDOWS:
            win_cursor(visible=False)
        else:
            sys.stderr.write("\033[?25l")
            sys.stderr.flush()


def show_cursor() -> None:
    if stderr_is_tty:
        if WINDOWS:
            win_cursor(visible=True)
        else:
            sys.stderr.write("\033[?25h")
            sys.stderr.flush()


def clear_line() -> None:
    """Clears current line and positions cursor at start of line"""
    sys.stderr.write(f"\r{CLEAR_LINE}")
    sys.stdout.write(f"\r{CLEAR_LINE}")
