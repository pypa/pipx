## pipx vs pip

- pip is a general Python package installer. It can be used to install libraries or CLI applications with entrypoints.
- pipx is a specialized package installer. It can only be used to install packages with CLI entrypoints.
- pipx and pip both install packages from PyPI (or locally)
- pipx relies on pip (and venv)
- pipx replaces a subset of pip's functionality; it lets you install CLI applications but NOT libraries that you import
    in your code.
- you can install pipx with pip

Example interaction: Install pipx with pip: `pip install --user pipx`

## pipx vs uv tool

Both [`uv tool`](https://docs.astral.sh/uv/concepts/tools/) and pipx install a Python tool into its own virtual
environment and expose the tool's console scripts on `PATH`. Both have a one-shot run mode (`uvx` and `pipx run`). `uvx`
is `uv tool run`. They differ in where state lives, which extra commands they ship, and how they handle managed Python.

pipx keeps the same CLI across pip and uv backends; `pipx install pipx[uv]` opts you into uv-speed venv creation without
changing any commands. `uv tool` ships a smaller per-tool surface, then reuses the rest of `uv` for free: managed
Python, content-addressed cache, lockfiles, PEP 723 script handling.

### Where state lives

|                        | pipx                                           | uv tool                                    |
| ---------------------- | ---------------------------------------------- | ------------------------------------------ |
| Per-tool venvs         | `$PIPX_HOME/venvs/<name>` (`PIPX_HOME`)        | `$UV_TOOL_DIR/<name>` (`UV_TOOL_DIR`)      |
| Exposed binaries       | `$PIPX_BIN_DIR` (default `~/.local/bin`)       | `$UV_TOOL_BIN_DIR` (default same)          |
| Man pages              | `$PIPX_MAN_DIR` (default `~/.local/share/man`) | _not exposed_                              |
| Shared pip/setup/wheel | `$PIPX_HOME/shared` (pip-backend only)         | _none; uv venvs ship without pip_          |
| Ephemeral run cache    | `$PIPX_HOME/.cache` (TTL 14 days)              | `$UV_CACHE_DIR` (no TTL; `uv cache prune`) |
| Standalone Python      | `$PIPX_HOME/py` (`PIPX_FETCH_PYTHON`)          | `$UV_PYTHON_INSTALL_DIR`                   |
| System-wide install    | `--global`, `PIPX_GLOBAL_*`                    | _not supported_                            |

`PIPX_BIN_DIR` and `UV_TOOL_BIN_DIR` both default to `~/.local/bin` on Unix, so installing the same tool with both
managers writes the same filename. Each manager refuses to overwrite a binary the other one wrote without `--force`. Use
`pipx install --suffix=...` to keep two copies side-by-side; uv has no equivalent.

### Subcommand mapping

| Task                           | pipx                                              | uv tool                                                             |
| ------------------------------ | ------------------------------------------------- | ------------------------------------------------------------------- |
| Install from PyPI              | `pipx install ruff`                               | `uv tool install ruff` (or `uvx ruff` for one-off)                  |
| Install from a git URL         | `pipx install 'git+https://…'`                    | `uv tool install 'git+https://…'`                                   |
| Install editable from path     | `pipx install -e ./mypkg`                         | `uv tool install -e ./mypkg`                                        |
| One-off run (no install)       | `pipx run black .`                                | `uvx black .`                                                       |
| One-off run with extra dep     | _no clean equivalent_                             | `uvx --with mkdocs-material mkdocs`                                 |
| Pinned-version one-off         | `pipx run --spec 'ruff==0.6.0' ruff check`        | `uvx ruff@0.6.0 check`                                              |
| Add a dep to existing tool     | `pipx inject mkdocs mkdocs-material`              | `uv tool install mkdocs --with mkdocs-material` (rebuilds)          |
| Remove an injected dep         | `pipx uninject mkdocs mkdocs-material`            | _rebuild without `--with`_                                          |
| Upgrade one                    | `pipx upgrade ruff`                               | `uv tool upgrade ruff`                                              |
| Upgrade all                    | `pipx upgrade-all`                                | `uv tool upgrade --all`                                             |
| List installed                 | `pipx list`                                       | `uv tool list` (`--show-with`, `--outdated`, …)                     |
| Reinstall (e.g. after Py bump) | `pipx reinstall ruff` / `reinstall-all`           | `uv tool upgrade --reinstall ruff` / `--all -p 3.13`                |
| Run pip inside a venv          | `pipx runpip <tool> -- pip ...`                   | _not supported (no pip in uv venvs)_                                |
| PATH setup                     | `pipx ensurepath`                                 | `uv tool update-shell`                                              |
| Show resolved env              | `pipx environment`                                | `uv tool dir`, `uv tool dir --bin`, `uv cache dir`, `uv python dir` |
| PEP 723 inline script          | `pipx run script.py` (with uv backend → `uv run`) | `uv run --script script.py`                                         |

### Only in pipx

- `pipx inject` / `uninject` add or remove a package in place. `uv tool install --with` reaches the same end state by
    rebuilding the venv.
- `pipx runpip <venv> -- ...` runs pip inside a tool's venv. uv venvs have no pip.
- `--include-deps` exposes entry points from every dependency. uv requires you to enumerate dep packages with
    `--with-executables-from`.
- `--suffix` keeps two copies of the same tool side-by-side.
- `--global` and the `PIPX_GLOBAL_*` variables drive a system-wide install.
- Manual pages get symlinked under `$PIPX_MAN_DIR`.
- `pipx install-all <spec.json>` rebuilds every venv from a `pipx list --json` snapshot for cross-machine migration.
- `[project.entry-points."pipx.run"]` declares pipx-specific runtime extras in the package metadata.
- `pipx environment` prints every variable and its resolved value in one place.

### Only in uv tool

- `uv tool list --outdated` queries newer versions without upgrading.
- `uv tool list` toggles columns via `--show-with`, `--show-paths`, `--show-version-specifiers`, `--show-extras`,
    `--show-python`.
- `uvx --with-editable PATH` adds editable extras for a one-off run.
- `uv tool upgrade --all -p 3.13` re-pins every tool to a different Python in one shot.
- `uv python install/list/find/pin/upgrade/uninstall` integrates managed Python; uv auto-fetches when the requested
    Python isn't installed.
- `--exclude-newer`, `--torch-backend`, and `--isolated` add reproducibility knobs that pipx forwards but doesn't add on
    its own.
- The content-addressed cache spans `uv pip`, `uv tool`, `uv run`, and `uv venv`. Wheels downloaded once get reused
    everywhere.

### Gotchas

- `uvx` reuses cached envs across invocations until you prune the cache (`uv cache clean`), pin a new version
    (`uvx black@latest`), or pass `--refresh`. `pipx run` also caches, but the temp venv expires after 14 days idle.
- `uvx` prefers a persistent install when one exists. After `uv tool install ruff`, plain `uvx ruff` reuses that env
    instead of building an ephemeral one. Pass `--isolated` to bypass.
- `uv tool` ignores project-local `.python-version` files. `uv run` honors them; tool envs do not. pipx never reads
    them; pass `--python` or set `PIPX_DEFAULT_PYTHON`.
- `uv python upgrade` only bumps patch versions. To move a tool from 3.12 to 3.13 run `uv tool upgrade --all -p 3.13`.
    pipx's equivalent is `reinstall-all --python python3.13`.
- `uv run --script` needs a real on-disk path. When `pipx run script.py` content arrives via URL or named pipe, the uv
    backend falls back to building a venv.

### Picking one

Pipx wins when you need its tool-specific extras: `inject`/`uninject`, `--global`, `--suffix`, manual pages, or
`pipx install-all` for migration. Install `pipx[uv]` to keep that surface and pick up uv-speed venv creation. Reach for
`uv tool` when you already drive uv for managed Python or `uv run --script` and want one binary for everything. Running
both is fine; the only collision point is the shared bin dir, and both sides refuse to overwrite without `--force`.

## pipx vs poetry and pipenv

- pipx is used solely for application consumption: you install CLI apps with it
- pipenv and poetry are CLI apps used to develop applications and libraries
- all three tools wrap pip and virtual environments for more convenient workflows

Example interaction: Install pipenv and poetry with pipx: `pipx install poetry` Run pipenv or poetry with pipx:
`pipx run poetry --help`

## pipx vs venv

- venv is part of Python's standard library in Python 3.2 and above
- venv creates "virtual environments" which are sandboxed python installations
- pipx heavily relies on the venv package

Example interaction: pipx installs packages to environments created with venv. `pipx install black --verbose`

## pipx vs pyenv

- pyenv manages python versions on your system. It helps you install versions like Python 3.6, 3.7, etc.
- pipx installs packages in virtual environments and exposes their entrypoints on your PATH

Example interaction: Install a Python interpreter with pyenv, then install a package using pipx and that new
interpreter: `pipx install black --python=python3.11` where python3.11 was installed on the system with pyenv

## pipx vs pipsi

- pipx and pipsi both install packages in a similar way
- pipx is under active development. pipsi is no longer maintained.
- pipx always makes sure you're using the latest version of pip
- pipx has the ability to run an app in one line, leaving your system unchanged after it finishes (`pipx run APP`) where
    pipsi does not
- pipx has the ability to recursively install binaries from dependent packages
- pipx adds more useful information to its output
- pipx has more CLI options such as upgrade-all, reinstall-all, uninstall-all
- pipx is more modern. It uses Python 3.6+, and the `venv` package in the Python3 standard library instead of the python
    2 package `virtualenv`.
- pipx works with Python homebrew installations while pipsi does not (at least on my machine)
- pipx defaults to less verbose output
- pipx allows you to see each command it runs by passing the --verbose flag
- pipx prints emojis 😀

Example interaction: None. Either one or the other should be used. These tools compete for a similar workflow.

### Migrating to pipx from pipsi

After you have installed pipx, run
[migrate_pipsi_to_pipx.py](https://raw.githubusercontent.com/pypa/pipx/main/scripts/migrate_pipsi_to_pipx.py). Why not
do this with your new pipx installation?

```
pipx run https://raw.githubusercontent.com/pypa/pipx/main/scripts/migrate_pipsi_to_pipx.py
```

## pipx vs brew

- Both brew and pipx install cli tools
- They install them from different sources. brew uses a curated repository specifically for brew, and pipx generally
    uses PyPI.

Example interaction: brew can be used to install pipx, but they generally don't interact much.

## pipx vs npx

- Both can run cli tools (npx will search for them in node_modules, and if not found run in a temporary environment.
    `pipx run` will search in `__pypackages__` and if not found run in a temporary environment)
- npx works with JavaScript and pipx works with Python
- Both tools attempt to make running executables written in a dynamic language (JS/Python) as easy as possible
- pipx can also install tools globally; npx cannot

Example interaction: None. These tools work for different languages.

## pipx vs pip-run

[pip-run](https://github.com/jaraco/pip-run) is focused on running **arbitrary Python code in ephemeral environments**
while pipx is focused on running **Python binaries in ephemeral and non-ephemeral environments**.

For example these two commands both install poetry to an ephemeral environment and invoke poetry with `--help`.

```
pipx run poetry --help
pip-run poetry -- -m poetry --help
```

Example interaction: None.

## pipx vs fades

[fades](https://github.com/PyAr/fades) is a tool to run **individual** Python scripts inside automatically provisioned
virtualenvs with their dependencies installed.

- Both [fades](https://github.com/PyAr/fades#how-to-mark-the-dependencies-to-be-installed) and
    [pipx run](../reference/examples.md#pipx-run-examples) allow specifying a script's dependencies in specially
    formatted comments, but the exact syntax differs. (pipx's syntax is standardized by a
    [provisional specification](https://packaging.python.org/en/latest/specifications/inline-script-metadata/), fades's
    syntax is not standardized.)
- Both tools automatically set up reusable virtualenvs containing the necessary dependencies.
- Both can download Python scripts/packages to execute from remote resources.
- fades can only run individual script files while pipx can also run packages.

Example interaction: None.

## pipx vs pae/pactivate

_pae_ is a Bash command-line function distributed with [pactivate](https://github.com/cynic-net/pactivate) that uses
pactivate to create non-ephemeral environments focused on general use, rather than just running command-line
applications.

There is [a very detailed comparison here](https://github.com/cynic-net/pactivate/blob/main/doc/vs-pipx.md), but to
briefly summarize:

Similarities:

- Both create isolated environments without having to specify (and remember) a directory in which to store them.
- Both allow you to use any Python interpreter available on your system (subject to version restrictions below).

pae advantages:

- Supports all versions of Python from 2.7 upward. pipx requires ≥3.10.
- Fewer dependencies. (See the detailed comparison for more information.)
- Easier to have multiple versions of a single program and/or use different Python versions for a single program.
- Somewhat more convenient for running arbitrary command-line programs in virtual environments, installing multiple
    packages in a single environment, and activating virtual environments.
- Integrates well with source code repos using [pactivate](https://github.com/cynic-net/pactivate).

pae disadvantages:

- Usable with Bash shell only.
- Slightly less quick and convenient for installing/running command-line programs from single Python packages.
- Can be slower than pipx at creating virtual environments.

Example interaction: None. Either one or the other should be used. These tools compete for a similar workflow.
