#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from contextlib import contextmanager
import sys
from typing import Dict
from threading import Thread
from time import sleep


@contextmanager
def animate(message: str, do_animation: bool):
    animate = {"do_animation": do_animation, "message": message}
    t = Thread(target=print_animation, args=(animate,))
    t.start()
    try:
        yield
    finally:
        animate["do_animation"] = False
        t.join(0)


def print_animation(meta: Dict[str, bool]):
    if not sys.stdout.isatty():
        return

    cur = "."
    longest_len = 0
    sleep(1)
    while meta["do_animation"]:
        if cur == "":
            cur = "."
        elif cur == ".":
            cur = ".."
        elif cur == "..":
            cur = "..."
        else:
            cur = ""
        message = f"{meta['message']}{cur}"
        longest_len = max(len(message), longest_len)
        sys.stdout.write(" " * longest_len)
        sys.stdout.write("\r")
        sys.stdout.write(message)
        sys.stdout.write("\r")
        sleep(0.5)
    sys.stdout.write(" " * longest_len)
    sys.stdout.write("\r")
