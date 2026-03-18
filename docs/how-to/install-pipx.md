## System Requirements

python 3.9+ is required to install pipx. pipx can run binaries from packages with Python 3.3+. Don't have Python 3.9 or
later? See [Python 3 Installation & Setup Guide](https://realpython.com/installing-python/).

You also need to have `pip` installed on your machine for `python3`. The installation process varies from system to
system. Consult [pip's installation instructions](https://pip.pypa.io/en/stable/installing/). Installing on Linux works
best with a
[Linux Package Manager](https://packaging.python.org/guides/installing-using-linux-tools/#installing-pip-setuptools-wheel-with-linux-package-managers).

pipx works on macOS, Linux, and Windows.

[![Packaging status](https://repology.org/badge/vertical-allrepos/pipx.svg?columns=3&exclude_unsupported=1)](https://repology.org/metapackage/pipx/versions)

## Installing pipx

### On macOS:

```
brew install pipx
pipx ensurepath
```

#### Additional (optional) commands

To allow pipx actions in global scope (requires pipx 1.5.0+):

```
sudo pipx ensurepath --global
```

To prepend the pipx bin directory to PATH instead of appending it (requires pipx 1.7.0+):

```
sudo pipx ensurepath --prepend
```

> [!NOTE]
> Some distributions ship older pipx versions (e.g. Ubuntu 24.04 ships v1.4.3). If `--global` or `--prepend` fails with
> "unrecognized arguments", upgrade pipx first: `pip install --user --upgrade pipx`, or install a newer version from a
> different source.

For more details, refer to [Customising your installation](configure-paths.md).

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

> [!NOTE]
> Distributions that adopt [PEP 668](https://peps.python.org/pep-0668/) (Ubuntu 23.04+, Debian 12+, Fedora 38+) mark the
> system Python as externally managed. Running `pip install --user` on these systems fails with an
> `externally-managed-environment` error. Use your distribution's package manager (`apt install pipx`,
> `dnf install pipx`) instead. If no distro package exists, install pipx inside its own virtual environment:
>
> ```
> python3 -m venv ~/.local/share/pipx-venv
> ~/.local/share/pipx-venv/bin/pip install pipx
> ln -s ~/.local/share/pipx-venv/bin/pipx ~/.local/bin/pipx
> pipx ensurepath
> ```

#### Additional (optional) commands

To allow pipx actions in global scope (requires pipx 1.5.0+):

```
sudo pipx ensurepath --global
```

To prepend the pipx bin directory to PATH instead of appending it (requires pipx 1.7.0+):

```
sudo pipx ensurepath --prepend
```

For more details, refer to [Customising your installation](configure-paths.md).

> [!NOTE]
> If you installed pipx with `pip install --user`, the `pipx` binary lives in your user directory (e.g.
> `~/.local/bin/pipx`). Running `sudo pipx` will fail because root's `PATH` does not include your user bin directory.
> Use the full path instead: `sudo ~/.local/bin/pipx ensurepath --global`. Alternatively, install pipx system-wide with
> `sudo pip install pipx` (without `--user`) or use your distribution's package manager.

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
> It is not recommended to install `pipx` via `pipx`. If you'd like to do this anyway, take a look at the
> [`pipx-in-pipx`](https://github.com/mattsb42-meta/pipx-in-pipx) project and read about the limitations there.

### On FreeBSD:

- Install via package manager

```sh
pkg install -y py311-pipx
```

- Install via pip

```sh
pip install --user pipx
pipx ensurepath
```

### Using pipx without installing (via zipapp)

The zipapp can be downloaded from [Github releases](https://github.com/pypa/pipx/releases) and you can invoke it with a
Python 3.9+ interpreter:

```
python pipx.pyz ensurepath
```

## Installing packages from source control

pipx accepts any source pip supports, including git repositories. Using `black` as an example:

```
pipx install git+https://github.com/psf/black.git
pipx install git+ssh://git@github.com/psf/black # using ssh
pipx install git+https://github.com/psf/black.git@branch  # branch of your choice
pipx install git+https://github.com/psf/black.git@ce14fa8b497bae2b50ec48b3bd7022573a59cdb1  # git hash
pipx install https://github.com/psf/black/archive/18.9b0.zip  # install a release
```

Use pip's `egg` syntax when installing extras:

```
pipx install "git+https://github.com/psf/black.git#egg=black[jupyter]"
```

### Installing from a pull request

To test a package from an open pull request, find the fork owner and branch name on the PR page, then build the git URL.
For example, PR #794 from user `contributor` on branch `fix-something`:

```
pipx install git+https://github.com/contributor/pipx.git@fix-something
```

If the PR branch has been merged, use the merge commit hash instead:

```
pipx install git+https://github.com/pypa/pipx.git@abc123def
```
