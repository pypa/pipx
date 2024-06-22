## `reinstall-all` fixes most issues

The following command should fix many problems you may encounter as a pipx user:

```
pipx reinstall-all
```

This is a good fix for the following problems:

- System python was upgraded and the python used with a pipx-installed package is no longer available
- pipx upgrade causes issues with old pipx-installed packages

pipx has been upgraded a lot over the years. If you are a long-standing pipx user (thanks, by the way!) then you may
have old pipx-installed packages that have internal data that is different than what pipx currently expects. By
executing `pipx reinstall-all`, pipx will re-write its internal data and this should fix many of issues you may
encounter.

**Note:** If your pipx-installed package was installed using a pipx version before 0.15.0.0 and you want to specify
particular options, then you may want to uninstall and install it manually:

```
pipx uninstall <mypackage>
pipx install <mypackage>
```

## Diagnosing problems using `list`

```
pipx list
```

will not only list all of your pipx-installed packages, but can also diagnose some problems with them, as well as
suggest solutions.

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

## `pipx` log files

Pipx records a verbose log file for every `pipx` command invocation. The logs for the last 10 `pipx` commands can be
found in `$XDG_STATE_HOME/pipx/logs` or user's log path if the former is not writable by the user.

For most users this location is `~/.local/state/pipx/logs`, where `~` is your home directory.

## Debian, Ubuntu issues

If you have issues using pipx on Debian, Ubuntu, or other Debian-based linux distributions, make sure you have the
following packages installed on your system. (Debian systems do not install these by default with their python
installations.)

```
sudo apt install python3-venv python3-pip
```

Reference:
[Python Packaging User Guide: Installing pip/setuptools/wheel with Linux Package Managers](https://packaging.python.org/guides/installing-using-linux-tools)

## macOS issues

If you want to use a Pipx-installed package in a shebang (a common example is the AWS CLI),
you will likely not be able to, because the binary will be stored under `~/Library/Application Support/pipx/`.
The space in the path is not supported in a shebang. A simple solution is symlinking
`~/Library/Application Support/pipx` to `~/Library/ApplicationSupport/pipx`, and using that as the
path in the shebang instead.

```
mkdir $HOME/Library/ApplicationSupport
ln -s $HOME/Library/Application\ Support/pipx $HOME/Library/ApplicationSupport/pipx
```

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

## Pipx files not in expected locations according to documentation

Pipx versions after 1.2.0 adopt the XDG base directory specification for the location of `PIPX_HOME` and the data,
cache, and log directories. Version 1.2.0 and earlier use `~/.local/pipx` as the default `PIPX_HOME` and install the
data, cache, and log directories under it. To maintain compatibility with older versions, pipx will automatically use
this old `PIPX_HOME` path if it exists. For a map of old and new paths, see
[Installation](installation.md#installation-options).

In Pipx version 1.5.0, this was reverted for Windows and MacOS. It defaults again to `~/.local/pipx` on MacOS and to
`~\pipx` on Windows.

If you have a `pipx` version later than 1.2.0 and want to migrate from the old path to the new paths, you can move the
`~/.local/pipx` directory to the new location (after removing cache, log, and trash directories which will get recreated
automatically) and then reinstall all packages.

Please refer to [Installation](installation.md#moving-your-pipx-installation) on how to move it.

## Warning: Found a space in the pipx home path

In pipx version 1.5, we introduced the warning you're seeing, as multiple incompatibilites with spaces in the pipx home path were discovered. You may see this for the following reasons:

1. From pipx version 1.3 to 1.5, we were by default using a path with a space on it on MacOS. This unfortunately means, that all users that installed pipx in this time frame and were using the default behavior are seeing this warning now.
2. You set your `PIPX_HOME` to a path with spaces in it explicitly or because your `$HOME` path contains a space.

### Why are spaces in the `PIPX_HOME` path bad

The main reason we can't support paths with spaces is that shebangs don't support spaces in the interpreter path. All applications installed via `pipx` are installed via `pip`, which creates a script with a shebang at the top, defining the interpreter of the `venv` to use.

`pip` does some magic to the shebang for scripts defined as a `script`, that resolves this issue. Unfortunately, many libraries define their scripts as `console_scripts`, where `pip` does not perform this logic. Therefore, these scripts cannot be run if installed with `pipx` in a path with spaces, as the path to the `venv` and therefore the interpreter to use will contain spaces.

If you want to use a script installed via pipx in a shebang itself (common for example for the aws cli), you run into a similar problem, as the path to the installed script will contain a space.

### How to fix

You can generally fix this by using our default locations, as long as your `$HOME` path does not contain spaces.
Please refer to our [Installation](installation.md#moving-your-pipx-installation) docs on how to move the `pipx` installation.

If you're really sure you want to stick to your path with spaces, to suppress the warning set the `PIPX_HOME_ALLOW_SPACE` environment variable to `true`.
