# Use the uv Backend

pipx can use [uv](https://github.com/astral-sh/uv) to create virtual environments, install packages, and run ephemeral
apps in place of pip and venv. The backend turns on when uv is reachable; flip it per command (`--backend`) or globally
(`PIPX_DEFAULT_BACKEND`).

> This page covers pipx using uv to create venvs and install packages. The pipx CLI surface stays the same. For a
> side-by-side comparison with `uv tool` (Astral's standalone command), see
> [pipx vs uv tool](../explanation/comparisons.md#pipx-vs-uv-tool).

## Why use it

- uv creates venvs faster than `python -m venv`. The venv ships without pip.
- uv resolves and installs faster than pip on large dependency trees.
- `pipx run` execs `uv tool run`, picking up uv's cross-invocation cache.

## Enable it

Two ways to expose uv to pipx:

1. Install pipx with the `uv` extra. pipx prefers the bundled binary when present:

    ```shell
    pipx install pipx[uv]
    ```

1. Install uv however you like (`brew install uv`, `cargo install uv`, etc.) and put it on `PATH`. pipx picks it up
    automatically.

When uv is available, pipx defaults to it for new venvs. Existing venvs keep their original backend; the choice lives in
each venv's metadata.

## Choose a backend explicitly

```shell
pipx install black --backend pip          # force pip + venv
pipx install ruff --backend uv            # force uv (errors if uv is not available)
PIPX_DEFAULT_BACKEND=uv pipx install ruff # global override via environment
pipx environment --value PIPX_RESOLVED_BACKEND  # see what pipx will use right now
```

`install`, `install-all`, `inject`, `upgrade`, `upgrade-all`, `reinstall`, `reinstall-all`, and `run` all accept
`--backend`. Run `pipx reinstall NAME --backend uv` to switch an already-installed venv.

## What changes under the uv backend

- pipx creates new venvs with `uv venv`. The venv contains no `pip` and no `pipx_shared.pth` file.
- `pipx runpip` runs `uv pip <args> --python <venv>/bin/python`. uv rejects flags it doesn't understand instead of pipx
    silently dropping them.
- `pipx run` execs `uv tool run`; the cache lives in uv's cache directory. Pass `--no-cache` to skip it.
- `pipx run script.py` execs `uv run --script script.py` for PEP 723 inline scripts.

## Limitations

- `pipx install pip --backend uv` errors out. A uv venv has no pip, so the result would be inconsistent. Use
    `--backend pip` instead.
- `pipx run --backend uv` does not honor `[pipx.run]` entry points; `uv tool run` only sees standard console scripts.
    Use `--backend pip` if your package declares them.
- Some `--pip-args` values have no `uv tool run` equivalent (for example `--editable`, `--no-build-isolation`). pipx
    errors instead of silently dropping them. Use `--backend pip` for those flows.
- `pipx run --backend uv` against URL or named-pipe scripts falls back to a pipx-managed venv: `uv run --script` reads
    PEP 723 metadata off disk, and there is no on-disk path for content fetched at runtime. pipx logs a warning when
    this fallback fires.

## Cache layout

`pipx run` under the uv backend caches in `UV_CACHE_DIR` instead of `PIPX_VENV_CACHEDIR`. Switching the default backend
on a host that already used `pipx run` leaves the old pipx cache behind: `pipx environment` prints both paths so you can
inspect them and remove the unused one manually. The 14-day expiry sweep that pipx applies to its own venv cache does
not extend to uv's cache, which uv manages on its own schedule (`uv cache clean`).
