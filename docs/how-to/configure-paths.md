## Installation Options

The default binary location for pipx-installed apps is `~/.local/bin`. This can be overridden with the environment
variable `PIPX_BIN_DIR`. The default manual page location for pipx-installed apps is `~/.local/share/man`. This can be
overridden with the environment variable `PIPX_MAN_DIR`. If the `--global` option is used, the default locations are
`/usr/local/bin` and `/usr/local/share/man` respectively and can be overridden with `PIPX_GLOBAL_BIN_DIR` and
`PIPX_GLOBAL_MAN_DIR`.

pipx's default virtual environment location is typically `~/.local/share/pipx` on Linux/Unix, `~/.local/pipx` on macOS
and `~\pipx` on Windows. For compatibility reasons, if `~/.local/pipx` on Linux, `%USERPROFILE%\AppData\Local\pipx` or
`~\.local\pipx` on Windows or `~/Library/Application Support/pipx` on macOS exists, it will be used as the default
location instead. This can be overridden with the `PIPX_HOME` environment variable. If the `--global` option is used,
the default location is always `/opt/pipx` and can be overridden with `PIPX_GLOBAL_HOME`.

In case one of these fallback locations exist, we recommend either manually moving the pipx files to the new default
location (see the [Moving your pipx installation](move-installation.md) section of the docs), or setting the `PIPX_HOME`
environment variable (discarding files existing in the fallback location).

As an example, you can install global apps accessible by all users on your system with either of the following commands
(on MacOS, Linux, and Windows WSL):

```
sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin PIPX_MAN_DIR=/usr/local/share/man pipx install <PACKAGE>
# or shorter (with pipx>=1.5.0)
sudo pipx install --global <PACKAGE>
```

> [!NOTE]
> After version 1.2.0, the default pipx paths have been moved from `~/.local/pipx` to specific user data directories on
> each platform using [platformdirs](https://pypi.org/project/platformdirs/) library
>
> | Old Path               | New Path                                   |
> | ---------------------- | ------------------------------------------ |
> | `~/.local/pipx/.trash` | `platformdirs.user_data_dir()/pipx/trash`  |
> | `~/.local/pipx/shared` | `platformdirs.user_data_dir()/pipx/shared` |
> | `~/.local/pipx/venvs`  | `platformdirs.user_data_dir()/pipx/venvs`  |
> | `~/.local/pipx/.cache` | `platformdirs.user_cache_dir()/pipx`       |
> | `~/.local/pipx/logs`   | `platformdirs.user_log_dir()/pipx/log`     |
>
> `user_data_dir()`, `user_cache_dir()` and `user_log_dir()` resolve to appropriate platform-specific user data, cache
> and log directories. See the
> [platformdirs documentation](https://platformdirs.readthedocs.io/en/latest/api.html#platforms) for details.
>
> This was reverted in 1.5.0 for Windows and macOS. We heavily recommend not using these locations on Windows and macOS
> anymore, due to multiple incompatibilities discovered with these locations, documented
> [here](troubleshoot.md#why-are-spaces-in-the-pipx_home-path-bad).

### Customising your installation

#### `--global` argument

The `--global` flag installs applications into a system-wide location accessible to all users. It must be placed
**after** the subcommand, not before it:

```
# correct
sudo pipx install --global pycowsay
sudo pipx list --global

# wrong (--global is silently ignored when placed before the subcommand)
sudo pipx --global install pycowsay
```

Default global paths are `/usr/local/bin` for binaries, `/usr/local/share/man` for man pages, and `/opt/pipx` for
virtual environments. Override them with `PIPX_GLOBAL_BIN_DIR`, `PIPX_GLOBAL_MAN_DIR`, and `PIPX_GLOBAL_HOME`. Run
`sudo pipx ensurepath --global` to add the global binary directory to the system `PATH`.

The `--global` flag is not supported on Windows.

#### `--prepend` argument

The `--prepend` argument can be passed to the `pipx ensurepath` command to prepend the `pipx` bin directory to the
user's PATH environment variable instead of appending to it. This can be useful if you want to prioritise
`pipx`-installed binaries over system-installed binaries of the same name.

### Configuring pip for pipx

pipx uses pip internally for all package installs, including its own shared libraries (pip, setuptools). To point pip at
a private index or pass custom options, set `PIP_*` environment variables. pipx forwards them to every pip invocation.

For example, to use a private package index:

```
export PIP_INDEX_URL=https://my-private-index.example.com/simple/
export PIP_TRUSTED_HOST=my-private-index.example.com
pipx install my-private-package
```

These variables also apply when pipx upgrades its shared libraries (`pipx upgrade-shared`). You can set them permanently
in your shell profile or in pip's own config file (`pip.conf` / `pip.ini`). See the
[pip configuration documentation](https://pip.pypa.io/en/stable/topics/configuration/) for details.

Per-command pip options can be passed with `--pip-args`:

```
pipx install my-package --pip-args='--no-cache-dir --trusted-host=my-host'
```
