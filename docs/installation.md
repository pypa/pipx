## System Requirements

python 3.7+ is required to install pipx. pipx can run binaries from packages with Python 3.3+. Don't have Python 3.7 or later? See [Python 3 Installation & Setup Guide](https://realpython.com/installing-python/).

You also need to have `pip` installed on your machine for `python3`. Installing it varies from system to system. Consult [pip's installation instructions](https://pip.pypa.io/en/stable/installing/). Installing on Linux works best with a [Linux Package Manager](https://packaging.python.org/guides/installing-using-linux-tools/#installing-pip-setuptools-wheel-with-linux-package-managers).

pipx works on macOS, linux, and Windows.

## Install pipx

On macOS:

```
brew install pipx
pipx ensurepath
```

On Windows (requires pip 19.0 or later):

```
py -3 -m pip install --user pipx
py -3 -m pipx ensurepath
```

Otherwise, install via pip (requires pip 19.0 or later):

```
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

Or via zipapp:

You can also use pipx without installing it.
The zipapp can be downloaded from [Github releases](https://github.com/pypa/pipx/releases) and you can invoke it with a Python 3.7+ interpreter:

```
python pipx.pyz ensurepath
```

### Installation Options

The default binary location for pipx-installed apps is `~/.local/bin`. This can be overridden with the environment variable `PIPX_BIN_DIR`.

pipx's default virtual environment location is `~/.local/pipx`. This can be overridden with the environment variable `PIPX_HOME`.

As an example, you can install global apps accessible by all users on your system with the following command (on MacOS, Linux, and Windows WSL):

```
sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install PACKAGE
# Example: $ sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install cowsay
```

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
