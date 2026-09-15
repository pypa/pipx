# pipx redirect site

This orphan branch is the GitHub Pages source for <https://pypa.github.io/pipx/>, the address the documentation used
before it moved to <https://pipx.pypa.io/>. It carries no project code, so the redirect stays out of `main`.

`index.html` covers the old front page. `404.html` covers every other path, because GitHub Pages serves it whenever a
request matches no file; its slug table maps each MkDocs page onto the Sphinx page it became, and unknown paths land on
the documentation root.

Repository settings point Pages at this branch. Adding a page to the documentation needs no change here; only renaming
or removing one of the old MkDocs slugs does.
