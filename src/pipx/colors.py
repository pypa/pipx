from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable

_PRINT_COLOR: Final[bool] = bool(sys.stdout and sys.stdout.isatty())

if sys.platform == "win32" and _PRINT_COLOR:
    # colorama, a Windows-only dependency, wraps the console so the ANSI escapes below render on legacy terminals
    import colorama

    colorama.init()


def _colorizer(start: str) -> Callable[[str], str]:
    def colorize(text: str) -> str:
        return f"{start}{text}\033[0m" if _PRINT_COLOR else text

    return colorize


BOLD: Final[Callable[[str], str]] = _colorizer("\033[1m")
RED: Final[Callable[[str], str]] = _colorizer("\033[91m")
GREEN: Final[Callable[[str], str]] = _colorizer("\033[92m")


__all__ = [
    "BOLD",
    "GREEN",
    "RED",
]
