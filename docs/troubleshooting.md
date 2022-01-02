## `reinstall-all` fixes most issues

The following command should fix many problems you may encounter as a pipx user:

```
pipx reinstall-all
```

This is a good fix for the following problems:

* System python was upgraded and the python used with a pipx-installed package is no longer available
* pipx upgrade causes issues with old pipx-installed packages

pipx has been upgraded a lot over the years.  If you are a long-standing pipx
user (thanks, by the way!) then you may have old pipx-installed packages that
have internal data that is different than what pipx currently expects.  By
executing `pipx reinstall-all`, pipx will re-write its internal data and this
should fix many of issues you may encounter.

**Note:** If your pipx-installed package was installed using a pipx version
before 0.15.0.0 and you want to specify particular options, then you may want
to uninstall and install it manually:

```
pipx uninstall <mypackage>
pipx install <mypackage>
```

## Diagnosing problems using `list`

```
pipx list
```

will not only list all of your pipx-installed packages, but can also diagnose
some problems with them, as well as suggest solutions.

## Specifying pipx options

The most reliable method to specify command-line options that require an
argument is to use an `=`-sign.  An example:
```
pipx install pycowsay --pip-args="--no-cache-dir"
```
Another example for ignoring ssl/tls errors:
```
pipx install termpair --pip-args '--trusted-host files.pythonhosted.org --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host github.com'"
```

## Check for `PIP_*` environment variables

pipx uses `pip` to install and manage packages.  If you see pipx exhibiting
strange behavior on install or upgrade, check that you don't have special
environment variables that affect `pip`'s behavior in your environment.

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

## `pipx` log files
Pipx records a verbose log file for every `pipx` command invocation.  The logs
for the last 10 `pipx` commands can be found in `$PIPX_HOME/logs`.

For most users this location is `~/.local/pipx/logs`, where `~` is your home
directory.

## Debian, Ubuntu issues

If you have issues using pipx on Debian, Ubuntu, or other Debian-based linux
distributions, make sure you have the following packages installed on your
system.  (Debian systems do not install these by default with their python
installations.)

```
sudo apt install python3-venv python3-pip
```

Reference: [Python Packaging User Guide: Installing pip/setuptools/wheel with Linux Package Managers](https://packaging.python.org/guides/installing-using-linux-tools)

## Does it work to install your package with `pip`?

This is a tip for advanced users.  An easy way to check if pipx is the problem
or a package you're trying to install is the problem, is to try installing it
using `pip`.  For example:

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

If installation into this "virtual environment" using pip fails, then it's
likely that the problem is with the package or your host system.

To clean up after this experiment:

```
rm -rf test_venv
```
