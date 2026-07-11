## Environment Variables

pipx reads the following environment variables. All are optional.

| Variable                                | Description                                                               | Default                                                                    |
| --------------------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `PIPX_HOME`                             | Root directory for pipx virtual environments.                             | `~/.local/share/pipx` (Linux), `~/.local/pipx` (macOS), `~\pipx` (Windows) |
| `PIPX_BIN_DIR`                          | Directory where pipx places application entry-point symlinks.             | `~/.local/bin`                                                             |
| `PIPX_MAN_DIR`                          | Directory where pipx places man page symlinks.                            | `~/.local/share/man`                                                       |
| `PIPX_GLOBAL_HOME`                      | Root directory for global (`--global`) virtual environments.              | `/opt/pipx`                                                                |
| `PIPX_GLOBAL_BIN_DIR`                   | Binary directory for global installs.                                     | `/usr/local/bin`                                                           |
| `PIPX_GLOBAL_MAN_DIR`                   | Man page directory for global installs.                                   | `/usr/local/share/man`                                                     |
| `PIPX_DEFAULT_PYTHON`                   | Python interpreter to use when `--python` is not passed.                  | `python3` (or `py` on Windows)                                             |
| `PIPX_DEFAULT_BACKEND`                  | Backend for new venvs: `pip` or `uv`.                                     | `uv` when uv is available, else `pip`                                      |
| `PIPX_SHARED_LIBS`                      | Override the shared libraries directory.                                  | `PIPX_HOME/shared`                                                         |
| `PIPX_FETCH_PYTHON`                     | When to fetch a standalone Python build: `always`, `missing`, or `never`. | `never`                                                                    |
| `PIPX_FETCH_MISSING_PYTHON`             | Deprecated, alias for `PIPX_FETCH_PYTHON=missing`.                        | _(unset)_                                                                  |
| `PIPX_DISABLE_SHARED_LIBS_AUTO_UPGRADE` | Set to `1` to skip automatic shared library upgrades.                     | _(unset)_                                                                  |
| `PIPX_HOME_ALLOW_SPACE`                 | Set to `true` to suppress the "space in PIPX_HOME" warning.               | _(unset)_                                                                  |
| `PIPX_USE_EMOJI`                        | Set to `0` to disable emoji output.                                       | `1`                                                                        |
| `PIPX_MAX_LOGS`                         | Maximum number of log files to keep in the logs directory.                | `10`                                                                       |

### Notes

`PIPX_HOME` has platform-specific fallback logic. If a legacy directory (e.g. `~/.local/pipx` on Linux) already exists,
pipx uses it instead of the new default. See [Configure Paths](../how-to/configure-paths.md) for details.

On Unix, a pipx installation that manages itself recovers `PIPX_HOME`, `PIPX_BIN_DIR`, and `PIPX_DEFAULT_PYTHON` from
its virtual environment when those variables are unset. The recovered values keep later shells attached to the same
installation.

pipx forwards standard `PIP_*` environment variables (e.g. `PIP_INDEX_URL`) when it invokes pip. See
[Troubleshooting](../how-to/troubleshoot.md#check-for-pip_-environment-variables) if unexpected pip behaviour occurs.

Run `pipx environment` to see the resolved value of all directory variables on your system.
