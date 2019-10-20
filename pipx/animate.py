import sys
from contextlib import contextmanager
from threading import Event, Thread
from typing import Generator, List
import shutil

from pipx.constants import emoji_support

stderr_is_tty = sys.stderr.isatty()

(TERM_COLS, TERM_ROWS) = shutil.get_terminal_size(fallback=(9999, 24))


@contextmanager
def animate(message: str, do_animation: bool) -> Generator[None, None, None]:

    if not do_animation or not stderr_is_tty:
        # no op
        yield
        return

    event = Event()

    if emoji_support:
        animate_at_beginning_of_line = True
        symbols = ["⣷", "⣯", "⣟", "⡿", "⢿", "⣻", "⣽", "⣾"]
        period = 0.1
    else:
        animate_at_beginning_of_line = False
        symbols = ["", ".", "..", "..."]
        period = 1

    thread_kwargs = {
        "message": message,
        "event": event,
        "symbols": symbols,
        "delay": 0,
        "period": period,
        "animate_at_beginning_of_line": animate_at_beginning_of_line,
    }

    hide_cursor()
    t = Thread(target=print_animation, kwargs=thread_kwargs)
    t.start()

    try:
        yield
    finally:
        event.set()
        clear_line()
        show_cursor()
        sys.stderr.write("\r")
        sys.stdout.write("\r")


def print_animation(
    *,
    message: str,
    event: Event,
    symbols: List[str],
    delay: float,
    period: float,
    animate_at_beginning_of_line: bool,
):
    while not event.wait(0):
        for s in symbols:
            if animate_at_beginning_of_line:
                cur_line = f"{s} {message}"
            else:
                cur_line = f"{message}{s}"

            clear_line()
            sys.stderr.write("\r")
            if len(cur_line) > TERM_COLS:
                sys.stderr.write(f"{cur_line:.{TERM_COLS-4}}...")
            else:
                sys.stderr.write(cur_line)
            if event.wait(period):
                break


def hide_cursor():
    sys.stderr.write("\033[?25l")


def show_cursor():
    sys.stderr.write("\033[?25h")


def clear_line():
    sys.stderr.write("\033[K")
    sys.stdout.write("\033[K")
