# pipx
Execute binaries from Python packages. Binaries are run from temporary virtualenvs that disappear when the program exits.

**pip** lets you install packages and use binaries and modules system-wide (or virtualenv-wide), but oftentimes you want to isolate the binaries that are installed. **pipx** lets you run Python binaries in isolated, ephemeral environments.

pipx also lets you install the package to the system in an isolated way, where you can still run the binaries globally.

pipx enforces best practices when installing packages. It uses virtual environments, never requires sudo, plays nicely with the Python ecosystem, and automatically tidies up after itself.

## Install pipx
```
curl https://raw.githubusercontent.com/cs01/pipx/master/get-pipx.py | python3
```
python 3.6+ is required to install pipx. Binaries can be run with Python 3.3+.

## use pipx to run a program with no commitment
For example, if you wanted to see the help text for the wonderful code formatter [black](https://github.com/ambv/black), you could simply run
```
pipx black --help
```
and your system would be unchanged after the process exited.

Why? Because pipx will create a temporary directory, create a virtualenv inside it, install black in the virtual env, invoke black with the `--help` flag, then erase the temporary directory leaving your system untouched.

You can also run files on the web:
```
> pipx https://gist.githubusercontent.com/cs01/fa721a17a326e551ede048c5088f9e0f/raw/6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py
pipx is working!
```

## (optionally) globally install binaries with pipx
If you liked the binary you tried with `pipx <binary>` and want to keep it around, you can install it and have it always available globally.
```
pipx install <package>
```
will create a virtualenv, install the package, and create symlinks to the package's binaries in a folder on your PATH.

## Uninstall pipx
```
pipx uninstall pipx
```

## API
```
pipx --help
usage:
    pipx [-h] [--package PACKAGE] [--python PYTHON] [-v] [--version] binary
    pipx [-h] {install,upgrade,upgrade-all,uninstall,uninstall-all,list} ...


Execute binaries from Python packages. Alternatively, safely install a package
in a virtualenv with its binaries available globally. pipx will install a
virtualenv for the package in /Users/cssmith/.local/pipx/venvs. Symlinks to
binaries are placed in /Users/cssmith/.local/bin. These locations can be
overridden with the environment variables PIPX_HOME and PIPX_BIN_DIR,
respectively.

optional arguments:
  -h, --help            show this help message and exit

subcommands:
  Get help for commands with pipx -h [command]

  {binary,install,upgrade,upgrade-all,uninstall,uninstall-all,list}
    binary              Run a named binary, such as `black`. Automatically
                        downloads a Python package to a temporary virtualenv.
                        The virtualenv is completely gone after the binary
                        exits. i.e. `pipx black --help` will download the
                        latest version of black from PyPI, run it in a
                        virtualenv with the --help flag, then exit and remove
                        the virtualenv.
    install             Install a package
    upgrade             Upgrade a package
    upgrade-all         Upgrade all packages
    uninstall           Uninstall a package
    uninstall-all       Uninstall all package, including pipx
    list                List installed packages
```

## Credits
pipx was inspired by [pipsi](https://github.com/mitsuhiko/pipsi) and [npx](https://github.com/zkat/npx).
