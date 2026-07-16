"""Sphinx configuration for the pipx documentation."""

from __future__ import annotations

import importlib
import inspect
import os
import sys
from datetime import datetime, timezone
from html import escape as html_escape
from importlib.metadata import version as distribution_version
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

from docutils import nodes

if TYPE_CHECKING:
    from sphinx.application import Sphinx

sys.path.insert(0, str(Path(__file__).parent / "_ext"))

project = "pipx"
author = "pipx contributors"
project_copyright = f"{datetime.now(tz=timezone.utc):%Y}, pipx contributors"
release = distribution_version("pipx")
version = ".".join(release.split(".")[:2])

# Recipes across the how-to guides share one implicit import, so set it up once for every doctest group.
doctest_global_setup = "import pipx"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",  # reference any section by its title, scoped per document to keep labels unique
    "sphinx.ext.doctest",  # run the testcode/testoutput examples so the docs cannot drift from the code
    "sphinx.ext.intersphinx",  # cross-link names into the CPython docs
    "sphinx.ext.linkcode",  # link each documented Python object to its source on GitHub
    "notfound.extension",  # a versioned 404 page that keeps its links absolute
    "sphinx_argparse_cli",  # generate the CLI reference from pipx.main.build_parser so it cannot drift
    "sphinx_autodoc_typehints",
    "sphinx_codeautolink",  # turn the names in code and doctest blocks into links to the reference
    "sphinx_copybutton",
    "sphinx_design",  # the card grid on the landing page
    "sphinx_issues",  # the :issue:/:pr: roles used in the changelog and notes
    "sphinx_last_updated_by_git",  # stamp each page with the date of its last git edit
    "sphinx_reredirects",  # 301 old URLs to their new home after a page moves
    "sphinx_sitemap",  # emit sitemap.xml over the built pages
    "sphinxcontrib.mermaid",  # the .. mermaid:: directive used across the explanation diagrams
    "sphinxcontrib.towncrier.ext",  # render unreleased news fragments as a draft changelog section
    "sphinxext.opengraph",  # OpenGraph tags so shared links preview well
    "llms_txt",  # generate llms.txt and llms-full.txt from the built tree at build-finished (docs/_ext)
]

html_theme = "furo"
html_title = "pipx"
# the logo is the pipx wordmark, so furo need not repeat the project name beside it in the sidebar
html_theme_options = {"sidebar_hide_name": True}
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_logo = "_static/logo.svg"
html_favicon = "_static/logo.svg"
# Read the Docs sets the versioned canonical URL; the fallback keeps canonical links and the sitemap working on a local
# or CI build. Sphinx emits a <link rel="canonical"> per page from this, and the sitemap and OpenGraph tags reuse it.
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "https://pipx.pypa.io/latest/")

# sphinx-sitemap reuses html_baseurl; the URL already carries the version segment, so the per-page scheme is just the
# page path. sphinxext-opengraph and sphinx-notfound-page derive their absolute URLs from the same base.
sitemap_url_scheme = "{link}"
ogp_site_url = html_baseurl
notfound_urls_prefix = urlsplit(html_baseurl).path

# autosectionlabel would collide on identical section titles across pages (several guides open with a "Verify it
# worked" heading), so scope each label to its document and only label the top two heading levels.
autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 2

# codeautolink threads the names in one page's code blocks together, so a name bound in an early block still resolves in
# a later one.
codeautolink_concat_default = True

# The console blocks keep a literal "$ " prompt so Pygments detects the prompt and highlights the command after it
# (custom.css restyles that glyph). Strip the prompt on copy and drop the output lines, so the clipboard holds just the
# command. The trailing space keeps the match from catching shell variables like $HOME.
copybutton_prompt_text = "$ "
copybutton_prompt_is_regexp = False

# Read the Docs builds from a shallow clone, so sphinx-last-updated-by-git cannot see far enough back to stamp some
# pages and warns "Git clone too shallow"; under -W that would fail the build. The stamp still resolves for pages within
# the clone depth and degrades to the build date otherwise.
suppress_warnings = ["git.too_shallow"]

# sphinx-reredirects maps a moved page's old docname to its new location. The MkDocs-to-Sphinx move kept every docname,
# so there is nothing to redirect yet; add an entry here whenever a page's path changes.
redirects: dict[str, str] = {}

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
nitpicky = True
always_document_param_types = True
python_use_unqualified_type_names = True
autodoc_member_order = "bysource"

issues_github_path = "pypa/pipx"
towncrier_draft_autoversion_mode = "draft"
towncrier_draft_include_empty = True
towncrier_draft_working_directory = Path(__file__).parent.parent

_GITHUB_BLOB = "https://github.com/pypa/pipx/blob"
_REPO_ROOT = Path(__file__).parent.parent


def linkcode_resolve(domain: str, info: dict[str, str]) -> str | None:
    """Link a documented Python object to the line range of its source on GitHub."""
    if domain != "py" or not info["module"]:
        return None
    try:
        module = importlib.import_module(info["module"])
    except ImportError:
        return None
    obj: object | None = module
    for part in info["fullname"].split("."):
        obj = getattr(obj, part, None)
    try:
        target = inspect.unwrap(obj)
        source_file = inspect.getsourcefile(target)
        lines, start = inspect.getsourcelines(target)
        relative = Path(source_file).resolve().relative_to(_REPO_ROOT)
    except (TypeError, OSError, ValueError):
        return None
    ref = os.environ.get("READTHEDOCS_GIT_IDENTIFIER", "main")
    return f"{_GITHUB_BLOB}/{ref}/{relative.as_posix()}#L{start}-L{start + len(lines) - 1}"


_DESCRIPTION_LIMIT = 160


def _add_page_description(
    app: Sphinx,  # noqa: ARG001
    pagename: str,  # noqa: ARG001
    templatename: str,  # noqa: ARG001
    context: dict[str, Any],
    doctree: nodes.document | None,
) -> None:
    """Give each page a ``<meta name="description">`` from its first paragraph so search results read well."""
    if doctree is None:
        return
    for paragraph in doctree.findall(nodes.paragraph):
        if not (text := " ".join(paragraph.astext().split())):
            continue
        summary = text if len(text) <= _DESCRIPTION_LIMIT else f"{text[: _DESCRIPTION_LIMIT - 1].rstrip()}…"
        tag = f'<meta name="description" content="{html_escape(summary, quote=True)}" />'
        context["metatags"] = context.get("metatags", "") + f"\n    {tag}"
        return


def setup(app: Sphinx) -> dict[str, Any]:
    """Register the per-page meta description hook."""
    app.connect("html-page-context", _add_page_description)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
