from __future__ import annotations

import re
from pathlib import Path

# MkDocs published every page as a directory, so links to one ended in a slash. Sphinx publishes <page>.html and Read
# the Docs serves the built tree as is, so the old shape returns 404. The terminator set covers a bare URL, a markdown
# link and a quoted value, because the Release Notes link lives in a TOML string.
MKDOCS_PAGE_URL = re.compile(r"""https://pipx\.pypa\.io/(?:latest|stable)/[^\s<>)\]"']*/(?=[\s<>)\]"']|$)""")

ROOT = Path(__file__).parents[1]
# pyproject.toml is in the list because its urls table feeds the PyPI sidebar, which is where the
# stale Release Notes link was reported from.
SEARCHED_GLOBS = ("*.md", "*.rst", "pyproject.toml", ".github/*.md", "docs/**/*.md", "docs/**/*.rst")


def test_documentation_links_do_not_use_mkdocs_page_urls() -> None:
    stale = [
        f"{path.relative_to(ROOT).as_posix()}: {url}"
        for glob in SEARCHED_GLOBS
        for path in sorted(ROOT.glob(glob))
        for url in MKDOCS_PAGE_URL.findall(path.read_text(encoding="utf-8"))
    ]

    assert stale == []
