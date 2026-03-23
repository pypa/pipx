## Environment Variables

pipx reads the following environment variables. All are optional.

| Variable                    | Description                                                  | Default                                                                    |
| --------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------------- |
| `PIPX_HOME`                 | Root directory for pipx virtual environments.                | `~/.local/share/pipx` (Linux), `~/.local/pipx` (macOS), `~\pipx` (Windows) |
| `PIPX_BIN_DIR`              | Directory where application entry-point symlinks are placed. | `~/.local/bin`                                                             |
| `PIPX_MAN_DIR`              | Directory where man page symlinks are placed.                | `~/.local/share/man`                                                       |
| `PIPX_GLOBAL_HOME`          | Root directory for global (`--global`) virtual environments. | `/opt/pipx`                                                                |
| `PIPX_GLOBAL_BIN_DIR`       | Binary directory for global installs.                        | `/usr/local/bin`                                                           |
| `PIPX_GLOBAL_MAN_DIR`       | Man page directory for global installs.                      | `/usr/local/share/man`                                                     |
| `PIPX_DEFAULT_PYTHON`       | Python interpreter to use when `--python` is not passed.     | `python3` (or `py` on Windows)                                             |
| `PIPX_SHARED_LIBS`          | Override the shared libraries directory.                     | `PIPX_HOME/shared`                                                         |
| `PIPX_FETCH_MISSING_PYTHON` | Fetch missing Python versions when `--python` is used.       | _(unset)_                                                                  |
| `PIPX_HOME_ALLOW_SPACE`     | Set to `true` to suppress the "space in PIPX_HOME" warning.  | _(unset)_                                                                  |
| `PIPX_USE_EMOJI`            | Set to `0` to disable emoji output.                          | `1`                                                                        |
| `PIPX_MAX_LOGS`             | Maximum number of log files to keep in the logs directory.   | `10`                                                                       |

### Notes

`PIPX_HOME` has platform-specific fallback logic. If a legacy directory (e.g. `~/.local/pipx` on Linux) already exists,
pipx uses it instead of the new default. See [Configure Paths](../how-to/configure-paths.md) for details.

Standard `PIP_*` environment variables (e.g. `PIP_INDEX_URL`) are forwarded to pip when pipx invokes it. See
[Troubleshooting](../how-to/troubleshoot.md#check-for-pip_-environment-variables) if unexpected pip behaviour occurs.

Run `pipx environment` to see the resolved value of every directory variable on your system.
