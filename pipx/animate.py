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
    else:
        symbols = ["", ".", "..", "..."]
        incremental_wait_time = 1
    max_symbol_len = max(len(s) for s in symbols)
    spaces = " " * (len(message) + max_symbol_len)
    clear_line = f"\r{spaces}\r"

    thread_kwargs = {
        "message": message,
        "clear_line": clear_line,
        "event": event,
        "symbols": symbols,
        "delay": 0,
        "incremental_wait_time": incremental_wait_time,
    }

    if do_animation and sys.stderr.isatty():
        t = Thread(target=print_animation, kwargs=thread_kwargs)
        t.start()

    try:
        yield
    finally:
        event.set()
        sys.stderr.write(clear_line)


def print_animation(
    *,
    message: str,
    clear_line: str,
    event: Event,
    symbols: List[str],
    delay: float,
    incremental_wait_time: float,
):
    if event.wait(delay):
        return
    while True:
        for s in symbols:
            cur_line = f"{message}{s}"
            sys.stderr.write(clear_line + cur_line + "\r")
            if event.wait(incremental_wait_time):
                return
