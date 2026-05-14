## Pin installed packages

Use `pipx pin` when you need to hold an installation at its current version. Pinned packages are skipped by
`pipx upgrade`, `pipx upgrade-all`, and `pipx reinstall`, so the environment keeps its existing app and dependency
versions until you unpin it.

- `pipx pin PACKAGE` — pins the main package and any injected packages in that virtual environment.
- `pipx pin PACKAGE --injected-only` — leaves the main package upgradable but pins every injected package instead.
- `pipx pin PACKAGE --skip PKG_A PKG_B` — pins injected packages except the ones you list (the flag implies
    `--injected-only`).
- `pipx unpin PACKAGE` — re-enables upgrades for the package and anything that was pinned with it.
- `pipx list --pinned` — shows every pinned environment; add `--include-injected` to see pinned injected packages.

pipx tracks the main package and any injected packages. It does not record individual transitive dependencies, so there
is no way to pin a single dependency in isolation. Pinning the main package protects its dependency set because pipx
skips running `pip install --upgrade` for that environment.
