# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is pipx

pipx installs Python CLI applications into isolated virtual environments and exposes their entry points on PATH. Each
app gets its own venv under `PIPX_HOME/venvs/`, preventing dependency conflicts. `pipx run` additionally supports
ephemeral venvs (including PEP 723 inline script metadata).

## Commands

**Primary dev tool is `tox` (uses `uv` internally).**

```bash
# Run tests for a specific Python version
tox run -e 3.13

# Run linting (ruff, mypy, pre-commit hooks)
tox run -e lint

# Build docs
tox run -e docs

# Create an editable dev environment
tox run -e dev

# Or install directly
python -m pip install -e .
```

**Running tests directly:**

```bash
pytest tests/                          # all tests
pytest tests/test_install.py -v        # single file
pytest tests/test_install.py::test_foo # single test
pytest --all-packages                  # exhaustive (slow, normally skipped)
```

**Changelog:** Every PR needs a fragment in `changelog.d/{issue_number}.{type}.md` (types: `feature`, `bugfix`, `doc`,
`removal`, `misc`). Built by `towncrier`.

## Architecture

```
src/pipx/
├── main.py              # CLI parser (argparse + argcomplete), entry point pipx.main:cli
├── venv.py              # Venv (single venv wrapper) + VenvContainer (manages PIPX_HOME/venvs/)
├── paths.py             # Resolves PIPX_HOME, PIPX_BIN_DIR, etc. via paths.ctx singleton
├── pipx_metadata_file.py # JSON metadata per venv: PackageInfo, PipxMetadata (v0.4)
├── venv_inspect.py      # Reads venv metadata, extracts entry points from distributions
├── shared_libs.py       # Shared pip venv to deduplicate common dependencies
├── interpreter.py       # Python interpreter resolution (PIPX_DEFAULT_PYTHON, system)
├── standalone_python.py # Downloads python-build-standalone builds; cached in PIPX_INTERPRETER_FOLDER
├── package_specifier.py # PEP 508 parsing and validation
├── util.py              # PipxError, run_subprocess wrappers, path helpers
├── constants.py         # Platform flags (WINDOWS/MACOS/LINUX), ExitCode values
└── commands/            # One module per CLI subcommand
    ├── install.py       # pipx install
    ├── run.py           # pipx run (ephemeral venv, PEP 723 support)
    ├── upgrade.py       # pipx upgrade / upgrade-all
    ├── inject.py        # pipx inject (add dep to existing venv)
    ├── uninject.py      # pipx uninject
    ├── uninstall.py     # pipx uninstall / uninstall-all
    ├── reinstall.py     # pipx reinstall (different Python)
    ├── list_packages.py # pipx list
    ├── pin.py           # pipx pin / unpin
    ├── interpreter.py   # pipx interpreter (manage standalone Pythons)
    ├── ensure_path.py   # pipx ensurepath
    ├── environment.py   # pipx environment
    ├── run_pip.py       # pipx runpip
    └── common.py        # Shared install/upgrade utilities
```

**Key design patterns:**

- All package management goes through the `Venv` class in `venv.py`.
- Each venv stores a `pipx_metadata.json` (see `pipx_metadata_file.py`) enabling reproducible upgrades and reinstalls.
- `paths.ctx` is a singleton resolving all configurable paths; tests override it via the `pipx_temp_env` fixture.
- New CLI subcommands: add a module under `commands/`, wire it in `main.py`.

## Tests

Tests live in `tests/`. Key infrastructure:

- **`conftest.py`**: `pipx_temp_env` fixture isolates each test with temporary `PIPX_HOME`/`PIPX_BIN_DIR`;
    `pipx_local_pypiserver` serves packages from a local cache to avoid network calls.
- **`helpers.py`**: `run_pipx_cli()` invokes the CLI in-process; `mock_legacy_venv()` tests backward-compat metadata
    migrations.
- **`package_info.py`**: Database of test package specs, apps, and dependencies.
- Tests marked `@pytest.mark.all_packages` are excluded from normal runs (use `--all-packages` flag).

## Linting

Line length is 121. Ruff handles formatting and a broad set of lint rules (see `pyproject.toml [tool.ruff]`). mypy runs
in strict mode. Run `tox run -e lint` or `pre-commit run --all-files` before pushing. \]
