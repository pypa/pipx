## System Requirements
python 3.6+ is required to install pipx. pipx can run binaries from packages with Python 3.3+. Don't have Python 3.6 or later? See [Python 3 Installation & Setup Guide](https://realpython.com/installing-python/).

pipx works on macOS, linux, and Windows.

## Install pipx

```
python3 -m pip install --user pipx
python3 -m userpath append ~/.local/bin
```

### Installation Options
pipx's default binary location is `~/.local/bin`. This can be overriden with te `PIPX_BIN_DIR` environment variable. If you override `PIPX_BIN_DIR`, make sure it is on your path by running `userpath append $PIPX_BIN_DIR`.

pipx's default virtual environment location is `~/.local/pipx`. This can be overriden with the environment variable `PIPX_HOME`.

## Install pipx Development Versions
New versions of pipx are published as beta or release candidates. These versions look something like `0.13.0b1`, where `b1` signifies the first beta release of version 0.13. These releases can be tested with
```
pip install --user pipx --upgrade --dev
```
Development occurs on the `dev` branch of this repository. If there is no such branch, that means there is no work currently in development for a new version.

