import logging
import shutil
import sys
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from threading import Event, Thread
from typing import Final

from pipx.constants import WINDOWS
from pipx.emojis import EMOJI_SUPPORT

STDERR_IS_TTY: Final[bool] = bool(sys.stderr and sys.stderr.isatty())

CLEAR_LINE: Final[str] = "\033[K"
EMOJI_ANIMATION_FRAMES: Final[tuple[str, ...]] = ("⣷", "⣯", "⣟", "⡿", "⢿", "⣻", "⣽", "⣾")
NONEMOJI_ANIMATION_FRAMES: Final[tuple[str, ...]] = ("", ".", "..", "...")
EMOJI_FRAME_PERIOD: Final[float] = 0.1
NONEMOJI_FRAME_PERIOD: Final[float] = 1
MINIMUM_COLS_ALLOW_ANIMATION: Final[int] = 16


if WINDOWS:
    import ctypes

    class _CursorInfo(ctypes.Structure):
        _fields_ = (("size", ctypes.c_int), ("visible", ctypes.c_byte))


def _env_supports_animation() -> bool:
    (term_cols, _) = shutil.get_terminal_size(fallback=(0, 0))
    return STDERR_IS_TTY and term_cols > MINIMUM_COLS_ALLOW_ANIMATION


@contextmanager
def animate(message: str, do_animation: bool, *, delay: float = 0) -> Generator[None, None, None]:
    pipx_logger = logging.getLogger("pipx")
    handler_level = pipx_logger.handlers[0].level if pipx_logger.handlers else 0
    if pipx_logger.handlers and handler_level > logging.WARNING:
        yield
        return

    if not do_animation or not _env_supports_animation():
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

    thread = Thread(
        target=print_animation,
        kwargs={
            "message": message,
            "event": event,
            "symbols": symbols,
            "delay": delay,
            "period": period,
            "animate_at_beginning_of_line": animate_at_beginning_of_line,
        },
    )
    thread.start()

    try:
        yield
    finally:
        event.set()
        thread.join()
        clear_line()


def print_animation(
    *,
    message: str,
    event: Event,
    symbols: Sequence[str],
    delay: float,
    period: float,
    animate_at_beginning_of_line: bool,
) -> None:
    (term_cols, _) = shutil.get_terminal_size(fallback=(9999, 24))
    event.wait(delay)
    while not event.wait(0):
        for symbol in symbols:
            if animate_at_beginning_of_line:
                max_message_len = term_cols - len(f"{symbol} ... ")
                current_line = f"{symbol} {message:.{max_message_len}}"
                if len(message) > max_message_len:
                    current_line += "..."
            else:
                max_message_len = term_cols - len("... ")
                current_line = f"{message:.{max_message_len}}{symbol}"

            clear_line()
            sys.stderr.write(current_line)
            sys.stderr.flush()
            if event.wait(period):
                break


# for Windows pre-ANSI-terminal-support (before Windows 10 TH2 (v1511))
# https://stackoverflow.com/a/10455937
def win_cursor(visible: bool) -> None:
    if sys.platform != "win32":  # hello mypy
        return
    ci = _CursorInfo()  # type: ignore[unreachable]
    handle = ctypes.windll.kernel32.GetStdHandle(-11)
    ctypes.windll.kernel32.GetConsoleCursorInfo(handle, ctypes.byref(ci))
    ci.visible = visible
    ctypes.windll.kernel32.SetConsoleCursorInfo(handle, ctypes.byref(ci))


def hide_cursor() -> None:
    if STDERR_IS_TTY:
        if WINDOWS:
            win_cursor(visible=False)
        else:
            sys.stderr.write("\033[?25l")
            sys.stderr.flush()


def show_cursor() -> None:
    if STDERR_IS_TTY:
        if WINDOWS:
            win_cursor(visible=True)
        else:
            sys.stderr.write("\033[?25h")
            sys.stderr.flush()


def clear_line() -> None:
    sys.stderr.write(f"\r{CLEAR_LINE}")
    sys.stdout.write(f"\r{CLEAR_LINE}")


__all__ = [
    "CLEAR_LINE",
    "EMOJI_ANIMATION_FRAMES",
    "EMOJI_FRAME_PERIOD",
    "NONEMOJI_ANIMATION_FRAMES",
    "NONEMOJI_FRAME_PERIOD",
    "animate",
    "hide_cursor",
    "show_cursor",
]
