from __future__ import annotations

import shutil
import textwrap


def pipx_wrap(text: str, subsequent_indent: str = "", *, keep_newlines: bool = False) -> str:
    """Dedent, strip, wrap to shell width. Don't break on hyphens, only spaces"""
    minimum_width = 40
    width = max(shutil.get_terminal_size((80, 40)).columns, minimum_width) - 2

    text = textwrap.dedent(text).strip()
    if keep_newlines:
        return "\n".join([
            textwrap.fill(
                line,
                width=width,
                subsequent_indent=subsequent_indent,
                break_on_hyphens=False,
            )
            for line in text.splitlines()
        ])
    return textwrap.fill(
        text,
        width=width,
        subsequent_indent=subsequent_indent,
        break_on_hyphens=False,
    )
