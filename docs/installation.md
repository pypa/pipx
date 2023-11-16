## System Requirements

python 3.7+ is required to install pipx. pipx can run binaries from packages with Python 3.3+. Don't have Python 3.7 or later? See [Python 3 Installation & Setup Guide](https://realpython.com/installing-python/).

You also need to have `pip` installed on your machine for `python3`. Installing it varies from system to system. Consult [pip's installation instructions](https://pip.pypa.io/en/stable/installing/). Installing on Linux works best with a [Linux Package Manager](https://packaging.python.org/guides/installing-using-linux-tools/#installing-pip-setuptools-wheel-with-linux-package-managers).

pipx works on macOS, linux, and Windows.

## Installing pipx

On macOS:

```
brew install pipx
pipx ensurepath
```

On Windows (requires pip 19.0 or later):

```
py -m pip install --user pipx
py -m pipx ensurepath
```

Otherwise, install via pip (requires pip 19.0 or later):

```
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

!!!caution
    It is not recommended to install `pipx` via `pipx`. If you'd like
    to do this anyway, take a look at the
    [`pipx-in-pipx`](https://github.com/mattsb42-meta/pipx-in-pipx) project and
    read about the limitations there.


### Using pipx without installing (via zipapp)
The zipapp can be downloaded from [Github releases](https://github.com/pypa/pipx/releases) and you can invoke it with a Python 3.7+ interpreter:

```
python pipx.pyz ensurepath
```

### <a name="pre-commit"></a> Using pipx with pre-commit

Pipx has [pre-commit](https://pre-commit.com/) support. This lets you run applications:

* That can be run using `pipx run` but don't have native pre-commit support.
* Using its prebuilt wheel from pypi.org instead of building it from source.
* Using pipx's `--spec` and `--index-url` flags.

Example configuration for use of the code linter [yapf](https://github.com/google/yapf/). This is to be added to your `.pre-commit-config.yaml`.

```yaml
- repo: https://github.com/pypa/pipx
  rev: 53e7f27
  hooks:
  - id: pipx
    alias: yapf
    name: yapf
    args: ['yapf', '-i']
    types: ['python']
```

## Installation Options

The default binary location for pipx-installed apps is `~/.local/bin`. This can be overridden with the environment variable `PIPX_BIN_DIR`.

pipx's default virtual environment location is typically `~/.local/share/pipx` on Linux/Unix, `%USERPROFILE%\AppData\Local\pipx` on Windows and `~/Library/Application Support/pipx` on macOS, and for compatibility reasons, if `~/.local/pipx` exists, it will be used as the default location instead. This can be overridden with the `PIPX_HOME` environment variable.

As an example, you can install global apps accessible by all users on your system with the following command (on MacOS, Linux, and Windows WSL):

```
sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install PACKAGE
# Example: $ sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install cowsay
```

!!! note

    After version 1.2.0, the default pipx paths have been moved from `~/.local/pipx` to specific user data directories on each platform using [platformdirs](https://pypi.org/project/platformdirs/) library

    | Old Path               | New Path                                   |
    | ---------------------- | ------------------------------------------ |
    | `~/.local/pipx/.trash` | `platformdirs.user_data_dir()/pipx/trash`  |
    | `~/.local/pipx/shared` | `platformdirs.user_data_dir()/pipx/shared` |
    | `~/.local/pipx/venvs`  | `platformdirs.user_data_dir()/pipx/venv`   |
    | `~/.local/pipx/.cache` | `platformdirs.user_cache_dir()/pipx`       |
    | `~/.local/pipx/logs`   | `platformdirs.user_log_dir()/pipx/log`     |
    
    `user_data_dir()`, `user_cache_dir()` and `user_log_dir()` resolve to appropriate platform-specific user data, cache and log directories. 
    See the [platformdirs documentation](https://platformdirs.readthedocs.io/en/latest/api.html#platforms) for details.

## Upgrade pipx

On macOS:

```
brew update && brew upgrade pipx
```

Otherwise, upgrade via pip:

```
python3 -m pip install --user -U pipx
```

### Note: Upgrading pipx from a pre-0.15.0.0 version to 0.15.0.0 or later

After upgrading to pipx 0.15.0.0 or above from a pre-0.15.0.0 version, you must re-install all packages to take advantage of the new persistent pipx metadata files introduced in the 0.15.0.0 release. These metadata files store pip specification values, injected packages, any custom pip arguments, and more in each main package's venv.

If you have no packages installed using the `--spec` option, and no venvs with injected packages, you can do this by running `pipx reinstall-all`.

If you have any packages installed using the `--spec` option or venvs with injected packages, you should reinstall packages manually using `pipx uninstall-all`, followed by `pipx install` and possibly `pipx inject`.

## Shell Completion

You can easily get your shell's tab completions working by following instructions printed with this command:

```
pipx completions
```

## Install pipx Development Versions

New versions of pipx are published as beta or release candidates. These versions look something like `0.13.0b1`, where `b1` signifies the first beta release of version 0.13. These releases can be tested with

```
pip install --user --upgrade --pre pipx
```
