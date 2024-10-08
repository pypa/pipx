Starting from version 1.8.0, pipx supports different backends and installers.

### Backends supported:
- `venv` (Default)
- `uv` (via `uv venv`)
- `virtualenv`

### Installers supported:
- `pip` (Default)
- `uv` (via `uv pip`)

> [!NOTE]
> If `uv` or `virtualenv` is not present in PATH, you should install them with `pipx install uv` or `pipx install virtualenv` in advance.

If you wish to use a different backend or installer, you can either:

- Pass command line arguments (`--backend`, `--installer`)
- Set environment variables (`PIPX_DEFAULT_BACKEND`, `PIPX_DEFAULT_INSTALLER`)

> [!NOTE]
> Command line arguments always have higher precedence than environment variables.

### Examples
```bash
# Use uv as backend and installer
pipx install --backend uv --installer uv black

# Use virtualenv as backend and uv as installer
pipx install --backend virtualenv --installer uv black
```

Use environment variables to set backend and installer:
```bash
export PIPX_DEFAULT_BACKEND=uv
export PIPX_DEFAULT_INSTALLER=uv
pipx install black
```
