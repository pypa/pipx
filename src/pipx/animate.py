import sys
from contextlib import contextmanager
from threading import Event, Thread
from typing import Generator, List
import shutil

from pipx.constants import emoji_support

stderr_is_tty = sys.stderr.isatty()


HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
CLEAR_LINE = "\033[K"
EMOJI_ANIMATION_FRAMES = ["⣷", "⣯", "⣟", "⡿", "⢿", "⣻", "⣽", "⣾"]
NONEMOJI_ANIMATION_FRAMES = ["", ".", "..", "..."]
EMOJI_FRAME_PERIOD = 0.1
NONEMOJI_FRAME_PERIOD = 1


@contextmanager
def animate(
    message: str, do_animation: bool, *, delay: float = 0
) -> Generator[None, None, None]:

    if not do_animation or not stderr_is_tty:
        # no op
        yield
        return

    event = Event()

    if emoji_support:
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
            sys.stderr.write("\r")
            sys.stderr.write(cur_line)
            if event.wait(period):
                break


def hide_cursor():
    sys.stderr.write(f"{HIDE_CURSOR}")


def show_cursor():
    sys.stderr.write(f"{SHOW_CURSOR}")


def clear_line():
    sys.stderr.write(f"{CLEAR_LINE}")
    sys.stdout.write(f"{CLEAR_LINE}")
