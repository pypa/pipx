from contextlib import contextmanager
import sys
from typing import List
from threading import Thread, Event
from pipx.constants import emoji_support


@contextmanager
def animate(message: str, do_animation: bool):
    event = Event()

    if emoji_support:
        symbols = ["⣷", "⣯", "⣟", "⡿", "⢿", "⣻", "⣽", "⣾"]
        message = message + " "
        incremental_wait_time = 0.1
        before = True
    else:
        symbols = ["", ".", "..", "..."]
        incremental_wait_time = 1
        before = False
    max_symbol_len = max(len(s) for s in symbols)
    spaces = " " * (len(message) + max_symbol_len + 2)

    thread_kwargs = {
        "message": message,
        "event": event,
        "symbols": symbols,
        "delay": 0,
        "incremental_wait_time": incremental_wait_time,
        "before": before,
    }

    if do_animation and sys.stderr.isatty():
        t = Thread(target=print_animation, kwargs=thread_kwargs)
        t.start()

    _hide_cursor()
    try:
        yield
    finally:
        event.set()
        sys.stderr.write("\r")
        clear_line()
        show_cursor()


def print_animation(
    *,
    message: str,
    event: Event,
    symbols: List[str],
    delay: float,
    incremental_wait_time: float,
    before: bool,
):
    if event.wait(delay):
        sys.stderr.write("\r")
        clear_line()
        return
    while True:
        for s in symbols:
            if before:
                cur_line = f"{s} {message}"
            else:
                cur_line = f"{message}{s}"

            sys.stderr.write("\r")
            clear_line()
            sys.stderr.write(cur_line)
            if event.wait(incremental_wait_time):
                sys.stderr.write("\r")
                clear_line()
                return


def _hide_cursor():
    sys.stderr.write("\033[?25l")


def show_cursor():
    sys.stderr.write("\033[?25h")


def clear_line():
    sys.stderr.write("\033[K")
