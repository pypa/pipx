## System Requirements

python 3.7+ is required to install pipx. pipx can run binaries from packages with Python 3.3+. Don't have Python 3.7 or
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
sudo pipx ensurepath --global # optional to allow pipx actions in global scope. See "Global installation" section below.
```

### On Linux:

- Ubuntu 23.04 or above

```
sudo apt update
sudo apt install pipx
pipx ensurepath
sudo pipx ensurepath --global # optional to allow pipx actions in global scope. See "Global installation" section below.
```

- Fedora:

```
sudo dnf install pipx
pipx ensurepath
sudo pipx ensurepath --global # optional to allow pipx actions in global scope. See "Global installation" section below.
```

- Using `pip` on other distributions:

```
python3 -m pip install --user pipx
python3 -m pipx ensurepath
sudo pipx ensurepath --global # optional to allow pipx actions in global scope. See "Global installation" section below.
```


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
Python 3.7+ interpreter:

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
  rev: 53e7f27
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
overridden with the environment variable `PIPX_MAN_DIR`.

pipx's default virtual environment location is typically `~/.local/share/pipx` on Linux/Unix,
`%USERPROFILE%\AppData\Local\pipx` on Windows and `~/Library/Application Support/pipx` on macOS, and for compatibility
reasons, if `~/.local/pipx` exists, it will be used as the default location instead. This can be overridden with the
`PIPX_HOME` environment variable.

As an example, you can install global apps accessible by all users on your system with the following command (on MacOS,
Linux, and Windows WSL):

```
sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin PIPX_MAN_DIR=/usr/local/share/man pipx install PACKAGE
# Example: $ sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin PIPX_MAN_DIR=/usr/local/share/man pipx install cowsay
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

### Global installation

Pipx also comes with a `--global` argument which helps to execute actions in global scope which exposes the app to
all system users. By default the global binary location is set to `/usr/local/bin` and can be overridden with the
environment variable `PIPX_GLOBAL_BIN_DIR`. Default global manual page location is `/usr/local/share/man`. This
can be overridden with environment variable `PIPX_GLOBAL_MAN_DIR`. Finally, default global virtual environment location
is `/opt/pipx`, can be overridden with environment variable `PIPX_GLOBAL_HOME`. Make sure to run `sudo pipx ensurepath --global`
if you intend to use this feature.

Note that the `--global` argument is not supported on Windows.

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
