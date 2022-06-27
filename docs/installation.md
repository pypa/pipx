## System Requirements

python 3.7+ is required to install pipx. pipx can run binaries from packages with Python 3.3+. Don't have Python 3.7 or later? See [Python 3 Installation & Setup Guide](https://realpython.com/installing-python/).

You also need to have `pip` and `venv` installed on your machine for `python3`. Installing pip varies from system to system. Consult [pip's installation instructions](https://pip.pypa.io/en/stable/installing/). Installing on Linux works best with a [Linux Package Manager](https://packaging.python.org/guides/installing-using-linux-tools/#installing-pip-setuptools-wheel-with-linux-package-managers).

pipx works on macOS, Linux, and Windows.

## Install pipx

### pipx installer for Linux, macOS, Windows

This method installs pipx in a temporary environment, then installs pipx _with pipx_. That's right, pipx is a command line tool, so installing it with itself isolates its dependencies just like any other python tool.

After it's finished, you can upgrade pipx with `pipx upgrade pipx`. To uninstall, you can run `pipx uninstall pipx`.

```
curl https://raw.githubusercontent.com/pypa/pipx/main/get-pipx.py | python3
```

for windows

```
(Invoke-WebRequest -Uri https://raw.githubusercontent.com/pypa/pipx/main/get-pipx.py -UseBasicParsing).Content | python -
```

You can replace `python3` with whichever python binary you want to install pipx with.

If python3 is not found on your PATH or there is a syntax error/typo, `curl` will fail with the error message: "(23) Failed writing body."

To pass arguments to the `get-pipx.py` script:

```
curl https://raw.githubusercontent.com/pypa/pipx/main/get-pipx.py | python3 - ARGS
```

For example, you can see options with

```
> curl https://raw.githubusercontent.com/pypa/pipx/main/get-pipx.py | python3 - --help
```

### brew

```
brew install pipx
pipx ensurepath
```

### pip

Install via pip (requires pip 19.0 or later):

```
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

### Linux Distributions

Linux distros also include pipx in their package managers. For example, you may be able to install with apt:

```
sudo apt install pipx
```

### Windows with pip

Install via pip (requires pip 19.0 or later):

```
python -m pip install --user pipx
```

If you installed python using the app-store, replace `python` with `python3` .

If you get the following warning

```
WARNING: The script pipx.exe is installed in `<USER folder>\AppData\Roaming\Python\Python3x\Scripts` which is not on PATH
```

go to the mentioned folder, allowing you to run the pipx executable directly. Enter the following line (even if you did not get the warning):

```
pipx ensurepath
```

This will add both the above mentioned path and the %USERPROFILE%.local\bin folder to your search path. Restart your terminal session and verify pipx runs.

### Windows with scoop

```
scoop bucket add pipx https://github.com/uranusjr/pipx-standalone.git
scoop install pipx
pipx ensurepath  # Adds PIPX_BIN_DIR to PATH to expose executables as commands.
```

See [https://github.com/uranusjr/pipx-standalone](https://github.com/uranusjr/pipx-standalone) for scoop build scripts.

### Installation Options

The default binary location for pipx-installed apps is `~/.local/bin`. This can be overridden with the environment variable `PIPX_BIN_DIR`.

pipx's default virtual environment location is `~/.local/pipx`. This can be overridden with the environment variable `PIPX_HOME`.

As an example, you can install global apps accessible by all users on your system with the following command (on MacOS, Linux, and Windows WSL):

```
sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install PACKAGE
# Example: $ sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install cowsay
```

## Upgrade pipx

Upgrade commands vary based on how pipx was installed on your system.

With `get-pipx.py` (an installation of pipx managed by itself):

```
pipx upgrade pipx
```

With brew:

```
brew update && brew upgrade pipx
```

With pip:

```
python3 -m pip install --user -U pipx
```

With apt:

```
sudo apt upgrade pipx
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
