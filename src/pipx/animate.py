from __future__ import annotations

__lazy_modules__ = ["logging", "pipx.fanout", "shutil", "threading"]

import logging
import shutil
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Event, Thread
from typing import TYPE_CHECKING, Final

from pipx.constants import WINDOWS
from pipx.emojis import EMOJI_SUPPORT
from pipx.fanout import output_is_held

if TYPE_CHECKING:
    from collections.abc import Generator

STDERR_IS_TTY: Final[bool] = bool(sys.stderr and sys.stderr.isatty())

CLEAR_LINE: Final[str] = "\033[K"
EMOJI_ANIMATION_FRAMES: Final[tuple[str, ...]] = ("⣷", "⣯", "⣟", "⡿", "⢿", "⣻", "⣽", "⣾")
NONEMOJI_ANIMATION_FRAMES: Final[tuple[str, ...]] = ("", ".", "..", "...")
_MINIMUM_COLS_ALLOW_ANIMATION: Final[int] = 16


if WINDOWS:
    import ctypes

    class _CursorInfo(ctypes.Structure):
        _fields_ = (("size", ctypes.c_int), ("visible", ctypes.c_byte))


@contextmanager
def animate(message: str, *, do_animation: bool, delay: float = 0) -> Generator[None, None, None]:
    if (handlers := logging.getLogger("pipx").handlers) and handlers[0].level > logging.WARNING:
        yield
        return

    if not do_animation or not _env_supports_animation():
        sys.stderr.write(f"{message}...\n")
        yield
        return

    # a spinner leaves nothing on screen once cleared, and replaying its frames later would only flicker
    if output_is_held():
        yield
        return

    event: Final[Event] = Event()
    thread: Final[Thread] = Thread(
        target=_print_animation,
        args=(
            message,
            event,
            delay,
            _Spinner(
                frames=EMOJI_ANIMATION_FRAMES if EMOJI_SUPPORT else NONEMOJI_ANIMATION_FRAMES,
                period=0.1 if EMOJI_SUPPORT else 1,
                at_line_start=EMOJI_SUPPORT,
            ),
        ),
    )
    thread.start()

    try:
        yield
    finally:
        event.set()
        thread.join()
        _clear_line()


def _env_supports_animation() -> bool:
    return STDERR_IS_TTY and shutil.get_terminal_size(fallback=(0, 0)).columns > _MINIMUM_COLS_ALLOW_ANIMATION


def _print_animation(message: str, event: Event, delay: float, spinner: _Spinner) -> None:
    term_cols: Final[int] = shutil.get_terminal_size(fallback=(9999, 24)).columns
    event.wait(delay)
    while not event.wait(0):
        for symbol in spinner.frames:
            if spinner.at_line_start:
                max_message_len = term_cols - len(f"{symbol} ... ")
                current_line = f"{symbol} {message:.{max_message_len}}"
                if len(message) > max_message_len:
                    current_line += "..."
            else:
                max_message_len = term_cols - len("... ")
                current_line = f"{message:.{max_message_len}}{symbol}"

            _clear_line()
            sys.stderr.write(current_line)
            sys.stderr.flush()
            if event.wait(spinner.period):
                break


def _clear_line() -> None:
    sys.stderr.write(f"\r{CLEAR_LINE}")
    sys.stdout.write(f"\r{CLEAR_LINE}")


@dataclass(frozen=True, slots=True, kw_only=True)
class _Spinner:
    frames: tuple[str, ...]
    period: float
    at_line_start: bool


def hide_cursor() -> None:
    if STDERR_IS_TTY:
        if WINDOWS:
            _win_cursor(visible=False)
        else:
            sys.stderr.write("\033[?25l")
            sys.stderr.flush()


# Windows consoles before Windows 10 TH2 (v1511) ignore ANSI escapes: https://stackoverflow.com/a/10455937
def _win_cursor(*, visible: bool) -> None:
    if sys.platform != "win32":  # narrows the platform so the type checker accepts ctypes.windll
        return
    cursor_info: Final[_CursorInfo] = _CursorInfo()
    handle: Final = ctypes.windll.kernel32.GetStdHandle(-11)
    ctypes.windll.kernel32.GetConsoleCursorInfo(handle, ctypes.byref(cursor_info))
    cursor_info.visible = visible
    ctypes.windll.kernel32.SetConsoleCursorInfo(handle, ctypes.byref(cursor_info))


def show_cursor() -> None:
    if STDERR_IS_TTY:
        if WINDOWS:
            _win_cursor(visible=True)
        else:
            sys.stderr.write("\033[?25h")
            sys.stderr.flush()


__all__ = [
    "CLEAR_LINE",
    "EMOJI_ANIMATION_FRAMES",
    "NONEMOJI_ANIMATION_FRAMES",
    "STDERR_IS_TTY",
    "animate",
    "hide_cursor",
    "show_cursor",
]
