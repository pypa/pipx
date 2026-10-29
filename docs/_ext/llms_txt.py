"""Generate ``llms.txt`` and ``llms-full.txt`` from the documentation tree at build time."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final, Protocol

from docutils import nodes

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment
    from sphinx.util.typing import ExtensionMetadata

# (docname prefix, heading) in the order the sections read; a docname's section is its first path segment, so
# ``reference`` and ``reference/cli`` both fall under Reference. Pages outside these prefixes (changelog, contributing)
# are left out of both files.
_SECTIONS: Final[tuple[tuple[str, str], ...]] = (
    ("tutorial", "Tutorials"),
    ("how-to", "How-to guides"),
    ("reference", "Reference"),
    ("explanation", "Explanation"),
)


def setup(app: Sphinx) -> ExtensionMetadata:
    app.connect("build-finished", _emit_llms_txt)
    return {"parallel_read_safe": True, "parallel_write_safe": True}


def _emit_llms_txt(app: Sphinx, exception: Exception | None) -> None:
    # https://llmstxt.org asks a site for a Markdown map of itself; kept by hand the two files drift from the pages they
    # list, so both come from the built tree, grouped by Diátaxis section in nav order
    if exception is not None or app.builder.name != "html":
        return
    env: Final = app.env
    root: Final[str] = env.config.root_doc
    base: Final[str] = app.config.html_baseurl.rstrip("/")
    order: Final[list[str]] = _ordered_docnames(env, root)
    titles: Final[dict[str, str]] = {
        docname: env.titles[docname].astext() for docname in [root, *order] if docname in env.titles
    }
    summaries: Final[dict[str, str]] = {docname: _summary(env, docname) for docname in titles}

    def link(docname: str, label: str | None = None) -> str:
        return f"- [{label or titles[docname]}]({base}/{docname}.html): {summaries.get(docname, '')}"

    grouped: Final[dict[str, list[str]]] = {key: [] for key, _ in _SECTIONS}
    # the section landing pages go under "Start here", not among their section's own pages
    index_pages: Final[set[str]] = {f"{key}/index" for key, _ in _SECTIONS}
    for docname in order:
        if (section := docname.split("/", 1)[0]) in grouped and docname not in index_pages:
            grouped[section].append(docname)

    project_summary: Final[str] = summaries.get(root, "")
    out: Final[Path] = Path(app.outdir)
    (out / "llms.txt").write_text(_render_curated(titles, grouped, project_summary, link), encoding="utf-8")
    (out / "llms-full.txt").write_text(_render_full(titles, grouped, project_summary, link), encoding="utf-8")


def _ordered_docnames(env: BuildEnvironment, root: str) -> list[str]:
    seen: Final[set[str]] = {root}
    order: Final[list[str]] = []
    stack: Final[list[str]] = list(reversed(env.toctree_includes.get(root, [])))
    while stack:
        docname = stack.pop()
        if docname in seen:
            continue
        seen.add(docname)
        order.append(docname)
        stack.extend(reversed(env.toctree_includes.get(docname, [])))
    return order


def _summary(env: BuildEnvironment, docname: str) -> str:
    for paragraph in env.get_doctree(docname).findall(nodes.paragraph):
        if text := " ".join(paragraph.astext().split()):
            return text
    return ""


def _render_curated(titles: dict[str, str], grouped: dict[str, list[str]], project_summary: str, link: _Link) -> str:
    lines: Final[list[str]] = [
        f"# {titles.get('index', 'pipx')}",
        "",
        f"> {project_summary}",
        "",
        (
            "The documentation follows the Diátaxis framework: tutorials to learn pipx by doing, how-to guides for "
            "specific tasks, a reference for the CLI and environment, and explanation for how pipx works and how it "
            "compares to other tools."
        ),
        "",
        "## Start here",
    ]
    lines.extend(
        link(docname, label)
        for docname, label in (
            ("index", "pipx overview"),
            ("tutorial/index", "Tutorials"),
            ("how-to/index", "How-to guides"),
            ("reference/index", "Reference"),
            ("explanation/index", "Explanation"),
        )
        if docname in titles
    )
    for key, heading in _SECTIONS:
        lines.extend(["", f"## {heading}", *[link(docname) for docname in grouped[key]]])
    return "".join(f"{line}\n" for line in lines)


class _Link(Protocol):
    def __call__(self, docname: str, label: str | None = None) -> str: ...


def _render_full(titles: dict[str, str], grouped: dict[str, list[str]], project_summary: str, link: _Link) -> str:
    lines: Final[list[str]] = [
        f"# {titles.get('index', 'pipx')} — full documentation map",
        "",
        f"> {project_summary}",
        "",
        (
            "Every documentation page, grouped by section, with a one-line description. Fetch a page's URL for its "
            "full content."
        ),
    ]
    for key, heading in _SECTIONS:
        if pages := grouped[key]:
            lines.extend(["", f"## {heading}", *[link(docname) for docname in pages]])
    return "".join(f"{line}\n" for line in lines)
