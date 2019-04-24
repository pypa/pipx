## System Requirements
python 3.6+ is required to install pipx. pipx can run binaries from packages with Python 3.3+. Don't have Python 3.6 or later? See [Python 3 Installation & Setup Guide](https://realpython.com/installing-python/).

pipx works on macOS, linux, and Windows.

## Install pipx
```
pip install --user pipx
userpath append ~/.local/bin
```

to be sure you are using python3 you can run

```
python3 -m pip install --user pipx
userpath append ~/.local/bin
```

If you want pipx to store binaries in a different location, you can set the environment variable `PIPX_BIN_DIR`, and ensure that location is on your path with `userpath append $PIPX_BIN_DIR`.

### Installing Development Versions
New versions of pipx are published as beta or release candidates. These versions look something like `0.13.0b1`, where `b1` signifies the first beta release of version 0.13. These releases can be tested with
```
pip install --user pipx --upgrade --dev
```
Development occurs on the `dev` branch of this repository. If there is no such branch, that means there is no work currently in development for a new version.

