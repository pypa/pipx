from __future__ import annotations

__lazy_modules__ = ["shutil", "textwrap", "typing"]

import shutil
import textwrap
from typing import Final


def pipx_wrap(text: str, subsequent_indent: str = "", *, keep_newlines: bool = False) -> str:
    """Wrap text to the width of the terminal, keeping paragraphs apart.

    :param text: the text to wrap, dedented and stripped first.
    :param subsequent_indent: the indent of the lines after the first one.
    :param keep_newlines: keep the line breaks of the text instead of joining its paragraphs.
    :returns: the wrapped text.
    """
    width: Final[int] = max(shutil.get_terminal_size((80, 40)).columns, 40) - 2
    dedented: Final[str] = textwrap.dedent(text).strip()
    return "\n".join(
        textwrap.fill(line, width=width, subsequent_indent=subsequent_indent, break_on_hyphens=False)
        for line in (dedented.splitlines() if keep_newlines else [dedented])
    )


__all__ = [
    "pipx_wrap",
]
