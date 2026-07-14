## Wrong package version installed

pipx creates venvs using your default Python interpreter. pip resolves the latest package version compatible with that
interpreter. If a package drops support for your Python version, pip installs an older release without warning.

Check which Python pipx uses with `pipx environment --value PIPX_DEFAULT_PYTHON`. To install with a different Python,
pass `--python`:

```
pipx install my-package --python python3.12
```

If you don't have the desired Python version installed, pass `--fetch-python=missing` and pipx downloads a standalone
build:

```
pipx install my-package --python 3.13 --fetch-python=missing
```

Pass `--fetch-python=always` to download a standalone build even when the system already has the requested Python.
Useful when a distro ships a patched interpreter you'd rather avoid.

## Diagnose and repair broken environments

Check each managed environment without changing it:

```
pipx health
```

The command exits with status 1 when an environment cannot run its Python interpreter. Pass package names to check a
subset, or pass `--output json` to read the result from a script.

Repair failed environments with the default Python:

```
pipx repair
```

Pass package names to limit the repair. Use `--python` when the rebuilt environments need another interpreter:

```
pipx repair --python python3.13
```

`pipx repair` uses the same recorded metadata as `pipx reinstall`. It leaves healthy environments unchanged.

`pipx repair` refuses a pinned package because its recorded source may resolve to another release. Run
`pipx unpin PACKAGE` before repairing it.

Use `pipx reinstall-all` to rebuild healthy environments, such as installations with metadata from an old pipx release.

**Note:** If your pipx-installed package was installed using a pipx version before 0.15.0.0 and you want to specify
particular options, then you may want to uninstall and install it manually:

```
pipx uninstall <mypackage>
pipx install <mypackage>
```

## Start over from a fresh install

An interrupted install or shared-library upgrade can leave state that `pipx repair` cannot mend, such as a shared
environment whose pip no longer imports. Reset pipx to the state it had when you installed it:

```
pipx reset
```

It uninstalls every package it manages, which unlinks their apps and man pages, and it removes the shared libraries, the
caches, the standalone interpreters, the logs and the trash. Because it asks first, `--force` answers the question for a
script, and `--dry-run` lists what it would remove without touching anything.

```
pipx reset --dry-run
```

Reinstall your packages afterwards. `pipx list --short` before the reset records what you had.

## Inspect package details with `list`

```
pipx list
```

The command prints package versions, applications, and environment paths.

## Specifying pipx options

The most reliable method to specify command-line options that require an argument is to use an `=`-sign. An example:

```
pipx install pycowsay --pip-args="--no-cache-dir"
```

Another example for ignoring ssl/tls errors:

```
pipx install termpair --pip-args '--trusted-host files.pythonhosted.org --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host github.com'"
```

## Check for `PIP_*` environment variables

pipx uses `pip` to install and manage packages. If you see pipx exhibiting strange behavior on install or upgrade, check
that you don't have special environment variables that affect `pip`'s behavior in your environment.

To check for `pip` environment variables, execute the following depending on your system:

### Unix or macOS

```
env | grep '^PIP_'
```

### Windows PowerShell

```
ls env:PIP_*
```

### Windows `cmd`

```
set PIP_
```

Reference: [pip Environment Variables](https://pip.pypa.io/en/stable/user_guide/#environment-variables)

## Clear `runpip` cache warnings

`pipx runpip` runs the `pip` installed in a pipx-managed virtual environment. Warnings such as
`WARNING: Cache entry deserialization failed, entry ignored` come from that `pip` process and its own HTTP cache, not
from pipx's virtual environment cache.

To clear the cache used by a pipx-managed package, run:

```
pipx runpip <package> cache purge
```

To inspect the cache directory first, add `--verbose` so pipx does not quiet `pip`'s output:

```
pipx runpip --verbose <package> cache dir
```

Clearing `$PIPX_HOME/.cache` or the cache for a different Python interpreter will not clear cache entries used by
`pipx runpip <package>`.

## `pipx` log files

pipx records a verbose log file for every `pipx` command invocation. The logs for the last 10 `pipx` commands can be
found in `$XDG_STATE_HOME/pipx/logs` or user's log path if the former is not writable by the user. Set `PIPX_MAX_LOGS`
to change how many log files are kept (default: `10`).

For most users this location is `~/.local/state/pipx/logs`, where `~` is your home directory.

## `sudo pipx` not found

If you installed pipx with `pip install --user`, the binary lives in your user directory (e.g. `~/.local/bin/pipx`).
Root's `PATH` does not include that directory, so `sudo pipx` fails with "command not found". Use the full path instead:

```
sudo ~/.local/bin/pipx ensurepath --global
```

To avoid this, install pipx through your distribution's package manager (`apt install pipx`, `dnf install pipx`) or
install it system-wide with `sudo pip install pipx` (without `--user`).

## Debian, Ubuntu issues

If you have issues using pipx on Debian, Ubuntu, or other Debian-based linux distributions, make sure you have the
following packages installed on your system. (Debian systems do not install these by default with their python
installations.)

```
sudo apt install python3-venv python3-pip
```

Reference:
[Python Packaging User Guide: Installing pip/setuptools/wheel with Linux Package Managers](https://packaging.python.org/guides/installing-using-linux-tools)

## Naming a pipx application in your own shebang

The default pipx home on macOS is `~/Library/Application Support/pipx`, which contains a space. Applications installed
there run, because `pip` and `uv` write a `/bin/sh` wrapper as the shebang whenever the interpreter path holds a space.

A shebang you write yourself has no such wrapper. `#!/Users/you/.local/bin/aws` works, while a shebang that names a path
with a space in it does not, because the kernel reads the first space as the end of the interpreter path. Point your
shebang at `PIPX_BIN_DIR` (`~/.local/bin` by default, which has no space), or set `PIPX_HOME` to a path without spaces.

## Does it work to install your package with `pip`?

This is a tip for advanced users. An easy way to check if pipx is the problem or a package you're trying to install is
the problem, is to try installing it using `pip`. For example:

### Unix or macOS

```
python3 -m venv test_venv
test_venv/bin/python3 -m pip install <problem-package>
```

### Windows

```
python -m venv test_venv
test_venv/Scripts/python -m pip install <problem-package>
```

If installation into this "virtual environment" using pip fails, then it's likely that the problem is with the package
or your host system.

To clean up after this experiment:

```
rm -rf test_venv
```

## pipx files not in expected locations according to documentation

pipx versions after 1.16.0 place `PIPX_HOME` and the data, cache and log directories in the platform locations that
[platformdirs](https://pypi.org/project/platformdirs/) reports. Earlier versions defaulted `PIPX_HOME` to
`~/.local/pipx`, or to `~/pipx` on Windows. pipx picks up such a directory when it exists, so an installation from an
earlier release keeps working. For a map of old and new paths, see [Installation Options](configure-paths.md).

The venv cache and the logs move to the platform cache and log directories even when pipx falls back to an older home,
because both are disposable and pipx recreates them. Setting `PIPX_HOME` yourself keeps them inside it.

To migrate an older installation, move the `~/.local/pipx` directory to the new location and reinstall your packages.
Please refer to [Moving your pipx installation](move-installation.md) on how to move it.

pipx adopted these paths in 1.2.0 and reverted them for macOS and Windows between 1.5.0 and 1.16.0.
