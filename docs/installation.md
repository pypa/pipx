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

Otherwise, install via pip (requires pip 19.0 or later):

```
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

### Installation Options

The default binary location for pipx-installed apps is `~/.local/bin`. This can be overridden with the environment variable `PIPX_BIN_DIR`.

pipx's default virtual environment location is `~/.local/pipx`. This can be overridden with the environment variable `PIPX_HOME`.

As an example, you can install global apps accessible by all users on your system with the following command (on MacOS, Linux, and Windows WSL):

```
sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install PACKAGE
# Example: $ sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install cowsay
```

## Private repositories requiring authentication

Two out of Pip's four supported methods of requesting credentials require additional effort. For Pip's side of the equation see [Pip's Authentication documentation](https://pip.pypa.io/en/stable/topics/authentication/) .

### Query the user via standard IO

You need to pass `--verbose` for this option to work as expected.

### Basic HTTP authentication

This should not require any additional effort.

### netrc support

This should not require any additional effort.

It does have the downside of storing the credential in plaintext and requiring the credential not to expire. (Or to be updated from time to time.)

### Keyring Support

In order to have keyring provide credentials the [keyring](https://pypi.org/project/keyring/) package needs to be importable immediately after Pipx created a virtual environment using Python's venv module.

For that first install [keyring-subprocess](https://pypi.org/project/keyring-subprocess/) since, unlike keyring, it has zero dependencies.

Secondly we install keyring and inject keyring-subprocess-landmark and the desired keyring backend into its venv.

```
# install keyring-subprocess, which is somewhat magical but needs a keyring-subprocess executable 
pipx install -i https://pypi.org/simple/ --shared keyring-subprocess

# install keyring, which provides the keyring executable
pipx install -i https://pypi.org/simple/ keyring

# inject keyring-subprocess-landmark, which provides the keyring-subprocess executable
pipx inject -i https://pypi.org/simple/ --include-apps keyring keyring-subprocess-landmark

# inject the actual backend needed for you private repository

# Microsoft Azure DevOps Artifact Feed:
pipx inject -i https://pypi.org/simple/ keyring artifacts-keyring
# Google Artifact Registry:
pipx inject -i https://pypi.org/simple/ keyring keyrings.google-artifactregistry-auth
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
