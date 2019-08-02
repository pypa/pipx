## System Requirements
python 3.6+ is required to install pipx. pipx can run binaries from packages with Python 3.3+. Don't have Python 3.6 or later? See [Python 3 Installation & Setup Guide](https://realpython.com/installing-python/).

You also need to have `pip` installed on your machine for `python3`. Installing it varies from system to system. Consult [pip's installation instructions](https://pip.pypa.io/en/stable/installing/). Installing on Linux works best with a [Linux Package Manager](https://packaging.python.org/guides/installing-using-linux-tools/#installing-pip-setuptools-wheel-with-linux-package-managers).

pipx works on macOS, linux, and Windows.

## Install pipx

Assuming you have `pip` installed for python3, run:
```
python3 -m pip install --user pipx
python3 -m ensurepath
```

### Installation Options
pipx's default binary location is `~/.local/bin`. This can be overriden with the environment variable `PIPX_BIN_DIR`.

pipx's default virtual environment location is `~/.local/pipx`. This can be overridden with the environment variable `PIPX_HOME`.

## Install pipx Development Versions
New versions of pipx are published as beta or release candidates. These versions look something like `0.13.0b1`, where `b1` signifies the first beta release of version 0.13. These releases can be tested with
```
pip install --user pipx --upgrade --dev
```
