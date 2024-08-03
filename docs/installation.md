## System Requirements

python 3.8+ is required to install pipx. pipx can run binaries from packages with Python 3.3+. Don't have Python 3.8 or
later? See [Python 3 Installation & Setup Guide](https://realpython.com/installing-python/).

You also need to have `pip` installed on your machine for `python3`. Installing it varies from system to system. Consult
[pip's installation instructions](https://pip.pypa.io/en/stable/installing/). Installing on Linux works best with a
[Linux Package Manager](https://packaging.python.org/guides/installing-using-linux-tools/#installing-pip-setuptools-wheel-with-linux-package-managers).

pipx works on macOS, linux, and Windows.

[![Packaging status](https://repology.org/badge/vertical-allrepos/pipx.svg?columns=3&exclude_unsupported=1)](https://repology.org/metapackage/pipx/versions)


## Installing pipx

### On macOS:

```
brew install pipx
pipx ensurepath
```

#### Additional (optional) commands

To allow pipx actions in global scope.
```
sudo pipx ensurepath --global
```

To prepend the pipx bin directory to PATH instead of appending it.

```
sudo pipx ensurepath --prepend
```

For more details, refer to [Customising your installation](#customising-your-installation).

### On Linux:

- Ubuntu 23.04 or above

```
sudo apt update
sudo apt install pipx
pipx ensurepath
```

- Fedora:

```
sudo dnf install pipx
pipx ensurepath
```

- Using `pip` on other distributions:

```
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

#### Additional (optional) commands

To allow pipx actions in global scope.

```
sudo pipx ensurepath --global
```

To prepend the pipx bin directory to PATH instead of appending it.

```
sudo pipx ensurepath --prepend
```

For more details, refer to [Customising your installation](#customising-your-installation).

### On Windows:

- Install via [Scoop](https://scoop.sh/):

```
scoop install pipx
pipx ensurepath
```

- Install via pip (requires pip 19.0 or later)

```
# If you installed python using Microsoft Store, replace `py` with `python3` in the next line.
py -m pip install --user pipx
```

It is possible (even most likely) the above finishes with a WARNING looking similar to this:

```
WARNING: The script pipx.exe is installed in `<USER folder>\AppData\Roaming\Python\Python3x\Scripts` which is not on PATH
```

If so, go to the mentioned folder, allowing you to run the pipx executable directly. Enter the following line (even if
you did not get the warning):

```
.\pipx.exe ensurepath
```

This will add both the above mentioned path and the `%USERPROFILE%\.local\bin` folder to your search path. Restart your
terminal session and verify `pipx` does run.

> [!WARNING]
>
> It is not recommended to install `pipx` via `pipx`. If you'd like to do this anyway, take a look at the
> [`pipx-in-pipx`](https://github.com/mattsb42-meta/pipx-in-pipx) project and read about the limitations there.

### Using pipx without installing (via zipapp)

The zipapp can be downloaded from [Github releases](https://github.com/pypa/pipx/releases) and you can invoke it with a
Python 3.8+ interpreter:

```
python pipx.pyz ensurepath
```

### <a name="pre-commit"></a> Using pipx with pre-commit

Pipx has [pre-commit](https://pre-commit.com/) support. This lets you run applications:

- That can be run using `pipx run` but don't have native pre-commit support.
- Using its prebuilt wheel from pypi.org instead of building it from source.
- Using pipx's `--spec` and `--index-url` flags.

Example configuration for use of the code linter [yapf](https://github.com/google/yapf/). This is to be added to your
`.pre-commit-config.yaml`.

```yaml
- repo: https://github.com/pypa/pipx
  rev: 1.5.0
  hooks:
    - id: pipx
      alias: yapf
      name: yapf
      args: ["yapf", "-i"]
      types: ["python"]
```

## Installation Options

The default binary location for pipx-installed apps is `~/.local/bin`. This can be overridden with the environment
variable `PIPX_BIN_DIR`. The default manual page location for pipx-installed apps is `~/.local/share/man`. This can be
overridden with the environment variable `PIPX_MAN_DIR`. If the `--global` option is used, the default locations are
`/usr/local/bin` and `/usr/local/share/man` respectively and can be overridden with `PIPX_GLOBAL_BIN_DIR` and
`PIPX_GLOBAL_MAN_DIR`.

pipx's default virtual environment location is typically `~/.local/share/pipx` on Linux/Unix, `~/.local/pipx` on MacOS
and `~\pipx` on Windows. For compatibility reasons, if `~/.local/pipx` on Linux, `%USERPROFILE%\AppData\Local\pipx` or
`~\.local\pipx` on Windows or `~/Library/Application Support/pipx` on MacOS exists, it will be used as the default location instead.
This can be overridden with the `PIPX_HOME` environment variable. If the `--global` option is used, the default location is always
`/opt/pipx` and can be overridden with `PIPX_GLOBAL_HOME`.

In case one of these fallback locations exist, we recommend either manually moving the pipx files to the new default location
(see the [Moving your pipx installation](installation.md#moving-your-pipx-installation) section of the docs), or setting the
`PIPX_HOME` environment variable (discarding files existing in the fallback location).

As an example, you can install global apps accessible by all users on your system with either of the following commands (on MacOS,
Linux, and Windows WSL):

```
sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin PIPX_MAN_DIR=/usr/local/share/man pipx install <PACKAGE>
# or shorter (with pipx>=1.5.0)
sudo pipx install --global <PACKAGE>
```

> [!NOTE]
>
> After version 1.2.0, the default pipx paths have been moved from `~/.local/pipx` to specific user data directories on
> each platform using [platformdirs](https://pypi.org/project/platformdirs/) library
>
> | Old Path               | New Path                                   |
> | ---------------------- | ------------------------------------------ |
> | `~/.local/pipx/.trash` | `platformdirs.user_data_dir()/pipx/trash`  |
> | `~/.local/pipx/shared` | `platformdirs.user_data_dir()/pipx/shared` |
> | `~/.local/pipx/venvs`  | `platformdirs.user_data_dir()/pipx/venv`   |
> | `~/.local/pipx/.cache` | `platformdirs.user_cache_dir()/pipx`       |
> | `~/.local/pipx/logs`   | `platformdirs.user_log_dir()/pipx/log`     |
>
> `user_data_dir()`, `user_cache_dir()` and `user_log_dir()` resolve to appropriate platform-specific user data, cache and log directories.
> See the [platformdirs documentation](https://platformdirs.readthedocs.io/en/latest/api.html#platforms) for details.
>
> This was reverted in 1.5.0 for Windows and MacOS. We heavily recommend not using these locations on Windows and MacOS anymore, due to
> multiple incompatibilities discovered with these locations, documented [here](troubleshooting.md#why-are-spaces-in-the-pipx_home-path-bad).

### Customising your installation

#### `--global` argument

Pipx also comes with a `--global` argument which helps to execute actions in global scope which exposes the app to
all system users. By default the global binary location is set to `/usr/local/bin` and can be overridden with the
environment variable `PIPX_GLOBAL_BIN_DIR`. Default global manual page location is `/usr/local/share/man`. This
can be overridden with environment variable `PIPX_GLOBAL_MAN_DIR`. Finally, default global virtual environment location
is `/opt/pipx`, can be overridden with environment variable `PIPX_GLOBAL_HOME`. Make sure to run `sudo pipx ensurepath --global`
if you intend to use this feature.

Note that the `--global` argument is not supported on Windows.

#### `--prepend` argument

The `--prepend` argument can be passed to the `pipx ensurepath` command to prepend the `pipx` bin directory to the user's PATH
environment variable instead of appending to it. This can be useful if you want to prioritise `pipx`-installed binaries over
system-installed binaries of the same name.

## Upgrade pipx

On macOS:

```
brew update && brew upgrade pipx
```

On Ubuntu Linux:

```
sudo apt upgrade pipx
```

On Fedora Linux:

```
sudo dnf update pipx
```


On Windows:

```
scoop update pipx
```

Otherwise, upgrade via pip:

```
python3 -m pip install --user -U pipx
```

### Note: Upgrading pipx from a pre-0.15.0.0 version to 0.15.0.0 or later

After upgrading to pipx 0.15.0.0 or above from a pre-0.15.0.0 version, you must re-install all packages to take
advantage of the new persistent pipx metadata files introduced in the 0.15.0.0 release. These metadata files store pip
specification values, injected packages, any custom pip arguments, and more in each main package's venv.

If you have no packages installed using the `--spec` option, and no venvs with injected packages, you can do this by
running `pipx reinstall-all`.

If you have any packages installed using the `--spec` option or venvs with injected packages, you should reinstall
packages manually using `pipx uninstall-all`, followed by `pipx install` and possibly `pipx inject`.

## Shell Completion

You can easily get your shell's tab completions working by following instructions printed with this command:

```
pipx completions
```

## Moving your pipx installation

The below code snippets show how to move your pipx installation to a new directory.
As an example, they move from a non-default location to the current default locations.
If you wish to move to a different location, just replace the `NEW_LOCATION` value.

### MacOS

Current default location: `~/.local`

```bash
NEW_LOCATION=~/.local
cache_dir=$(pipx environment --value PIPX_VENV_CACHEDIR)
logs_dir=$(pipx environment --value PIPX_LOG_DIR)
trash_dir=$(pipx environment --value PIPX_TRASH_DIR)
home_dir=$(pipx environment --value PIPX_HOME)
rm -rf "$cache_dir" "$logs_dir" "$trash_dir"
mkdir -p $NEW_LOCATION && mv "$home_dir" $NEW_LOCATION
pipx reinstall-all
```

### Linux

Current default location: `~/.local/share`

```bash
cache_dir=$(pipx environment --value PIPX_VENV_CACHEDIR)
logs_dir=$(pipx environment --value PIPX_LOG_DIR)
trash_dir=$(pipx environment --value PIPX_TRASH_DIR)
home_dir=$(pipx environment --value PIPX_HOME)
# If you wish another location, replace the expression below
# and set `NEW_LOCATION` explicitly
NEW_LOCATION="${XDG_DATA_HOME:-$HOME/.local/share}"
rm -rf "$cache_dir" "$logs_dir" "$trash_dir"
mkdir -p $NEW_LOCATION && mv "$home_dir" $NEW_LOCATION
pipx reinstall-all
```

### Windows

Current default location: `~/pipx`

```powershell
$NEW_LOCATION = Join-Path "$HOME" 'pipx'
$cache_dir = pipx environment --value PIPX_VENV_CACHEDIR
$logs_dir = pipx environment --value PIPX_LOG_DIR
$trash_dir = pipx environment --value PIPX_TRASH_DIR
$home_dir = pipx environment --value PIPX_HOME

Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$cache_dir", "$logs_dir", "$trash_dir"

# Remove the destination directory to ensure rename behavior of `Move-Item`
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$NEW_LOCATION"

Move-Item -Path $home_dir -Destination "$NEW_LOCATION"
pipx reinstall-all
```

If you would prefer doing it in bash via git-bash/WSL, feel free to use
the MacOS/Linux instructions, changing the `$NEW_LOCATION` to the Windows
version.
