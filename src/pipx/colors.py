import sys
from typing import Callable

import colorama  # type: ignore

PRINT_COLOR = sys.stdout.isatty()

if PRINT_COLOR:
    colorama.init()


class c:
    header = "\033[95m"
    blue = "\033[94m"
    green = "\033[92m"
    yellow = "\033[93m"
    red = "\033[91m"
    bold = "\033[1m"
    cyan = "\033[96m"
    underline = "\033[4m"
    end = "\033[0m"


def mkcolorfunc(style: str) -> Callable[[str], str]:
    def stylize_text(x: str) -> str:
        if PRINT_COLOR:
            return f"{style}{x}{c.end}"
        else:
            return x

    return stylize_text


bold = mkcolorfunc(c.bold)
red = mkcolorfunc(c.red)
blue = mkcolorfunc(c.cyan)
cyan = mkcolorfunc(c.blue)
green = mkcolorfunc(c.green)
