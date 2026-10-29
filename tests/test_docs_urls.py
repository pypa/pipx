from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path


def test_documentation_links_do_not_use_mkdocs_page_urls(root: Path) -> None:
    # MkDocs published every page as a directory, so links to one ended in a slash. Sphinx publishes <page>.html and
    # Read the Docs serves the built tree as is, so the old shape returns 404. The terminator set covers a bare URL, a
    # markdown link and a quoted value, because the Release Notes link lives in a TOML string.
    mkdocs_page_url: Final[re.Pattern[str]] = re.compile(
        r"""https://pipx\.pypa\.io/(?:latest|stable)/[^\s<>)\]"']*/(?=[\s<>)\]"']|$)"""
    )
    stale: Final[list[str]] = [
        f"{path.relative_to(root).as_posix()}: {url}"
        # pyproject.toml's urls table feeds the PyPI sidebar, where a user reported the stale Release Notes link
        for glob in ("*.md", "*.rst", "pyproject.toml", ".github/*.md", "docs/**/*.md", "docs/**/*.rst")
        for path in sorted(root.glob(glob))
        for url in mkdocs_page_url.findall(path.read_text(encoding="utf-8"))
    ]

    assert stale == []
