"""
Generate ``llms.txt`` and ``llms-full.txt`` from the documentation tree at build time.

The `llmstxt.org <https://llmstxt.org>`_ convention asks a site to publish a Markdown map of itself for language models:
a curated ``llms.txt`` index and a fuller ``llms-full.txt`` dump. Kept by hand, the two files drift from the pages they
list, so this extension derives both from the built tree. On ``build-finished`` it walks the root toctree in nav order,
reads each page's title and first paragraph, groups the pages by Diátaxis section, and writes the two files into the
HTML output root. ``html_baseurl`` supplies the absolute URLs.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from docutils import nodes

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment

# (docname prefix, heading) in the order the sections read; a docname's section is its first path segment, so
# ``reference`` and ``reference/cli`` both fall under Reference. Pages outside these prefixes (changelog, contributing)
# are left out of both files.
_SECTIONS: Final[tuple[tuple[str, str], ...]] = (
    ("tutorial", "Tutorials"),
    ("how-to", "How-to guides"),
    ("reference", "Reference"),
    ("explanation", "Explanation"),
)

# the landing page of each section; listed under "Start here", not enumerated with the section's own pages
_SECTION_INDEX: Final[dict[str, str]] = {
    "tutorial": "tutorial/index",
    "how-to": "how-to/index",
    "reference": "reference/index",
    "explanation": "explanation/index",
}

_START_HERE: Final[tuple[tuple[str, str], ...]] = (
    ("index", "pipx overview"),
    ("tutorial/index", "Tutorials"),
    ("how-to/index", "How-to guides"),
    ("reference/index", "Reference"),
    ("explanation/index", "Explanation"),
)

_DIATAXIS_NOTE: Final = (
    "The documentation follows the Diátaxis framework: tutorials to learn pipx by doing, how-to guides for specific "
    "tasks, a reference for the CLI and environment, and explanation for how pipx works and how it compares to other "
    "tools."
)


def setup(app: Sphinx) -> dict[str, Any]:
    """Register the build-finished hook that writes the two llms map files."""
    app.connect("build-finished", _emit_llms_txt)
    return {"parallel_read_safe": True, "parallel_write_safe": True}


def _emit_llms_txt(app: Sphinx, exception: Exception | None) -> None:
    """Write llms.txt and llms-full.txt into the HTML output root once the build succeeds."""
    if exception is not None or app.builder.name != "html":
        return
    env = app.env
    root = env.config.root_doc
    base = app.config.html_baseurl.rstrip("/")
    order = _ordered_docnames(env, root)
    titles = {docname: env.titles[docname].astext() for docname in [root, *order] if docname in env.titles}
    summaries = {docname: _summary(env, docname) for docname in titles}

    def link(docname: str, label: str | None = None) -> str:
        return f"- [{label or titles[docname]}]({base}/{docname}.html): {summaries.get(docname, '')}"

    grouped: dict[str, list[str]] = {key: [] for key, _ in _SECTIONS}
    index_pages = set(_SECTION_INDEX.values())
    for docname in order:
        section = _section_of(docname)
        if section in grouped and docname not in index_pages:
            grouped[section].append(docname)

    project_summary = summaries.get(root, "")
    out = Path(app.outdir)
    (out / "llms.txt").write_text(_render_curated(titles, grouped, project_summary, link), encoding="utf-8")
    (out / "llms-full.txt").write_text(_render_full(titles, grouped, project_summary, link), encoding="utf-8")


def _ordered_docnames(env: BuildEnvironment, root: str) -> list[str]:
    """Return every docname reachable from ``root`` in navigation order, each once."""
    seen = {root}
    order: list[str] = []
    stack = list(reversed(env.toctree_includes.get(root, [])))
    while stack:
        docname = stack.pop()
        if docname in seen:
            continue
        seen.add(docname)
        order.append(docname)
        stack.extend(reversed(env.toctree_includes.get(docname, [])))
    return order


def _summary(env: BuildEnvironment, docname: str) -> str:
    """Return the page's first paragraph, whitespace collapsed onto one line."""
    for paragraph in env.get_doctree(docname).findall(nodes.paragraph):
        if text := " ".join(paragraph.astext().split()):
            return text
    return ""


def _section_of(docname: str) -> str:
    return docname.split("/", 1)[0]


def _render_curated(
    titles: dict[str, str],
    grouped: dict[str, list[str]],
    project_summary: str,
    link: Callable[..., str],
) -> str:
    lines = [
        f"# {titles.get('index', 'pipx')}",
        "",
        f"> {project_summary}",
        "",
        _DIATAXIS_NOTE,
        "",
        "## Start here",
    ]
    lines += [link(docname, label) for docname, label in _START_HERE if docname in titles]
    for key, heading in _SECTIONS:
        lines += ["", f"## {heading}", *[link(docname) for docname in grouped[key]]]
    return "\n".join(lines) + "\n"


def _render_full(
    titles: dict[str, str],
    grouped: dict[str, list[str]],
    project_summary: str,
    link: Callable[..., str],
) -> str:
    note = (
        "Every documentation page, grouped by section, with a one-line description. Fetch a page's URL for its full "
        "content."
    )
    lines = [f"# {titles.get('index', 'pipx')} — full documentation map", "", f"> {project_summary}", "", note]
    for key, heading in _SECTIONS:
        if pages := grouped[key]:
            lines += ["", f"## {heading}", *[link(docname) for docname in pages]]
    return "\n".join(lines) + "\n"
