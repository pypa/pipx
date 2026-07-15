from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

PRINT_COLOR = bool(sys.stdout and sys.stdout.isatty())

if sys.platform == "win32" and PRINT_COLOR:
    # colorama, a Windows-only dependency, wraps the console so the ANSI escapes below render on legacy terminals
    import colorama

    colorama.init()


class _Colors:
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
            return f"{style}{x}{_Colors.end}"
        return x

    return stylize_text


bold = mkcolorfunc(_Colors.bold)
red = mkcolorfunc(_Colors.red)
blue = mkcolorfunc(_Colors.cyan)
cyan = mkcolorfunc(_Colors.blue)
green = mkcolorfunc(_Colors.green)
