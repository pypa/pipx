<p align="center">
<img align="center" src="https://github.com/pipxproject/pipx/raw/master/logo.png"/>
</p>

# pipx: execute binaries from Python packages in isolated environments

<p align="center">
<a href="https://github.com/pipxproject/pipx/raw/master/pipx_demo.gif">
<img src="https://github.com/pipxproject/pipx/raw/master/pipx_demo.gif"/>
</a>
</p>

<p align="center">
<a href="https://travis-ci.org/pipxproject/pipx"><img src="https://travis-ci.org/pipxproject/pipx.svg?branch=master" /></a>

<a href="https://pypi.python.org/pypi/pipx/">
<img src="https://img.shields.io/badge/pypi-0.13.0.0-blue.svg" /></a>
<a href="https://github.com/ambv/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

*For comparison to pipsi, see [how does this compare to pipsi?](#how-does-this-compare-to-pipsi) and [migrating to pipx from pipsi](#migrating-to-pipx-from-pipsi).*

*pipx uses the word "binary" to describe a CLI application that can be run directly from the command line. These files are located in the `bin` directory of a Python installation, alongside other executables. Despite the name, they do not necessarily contain binary data.*

## Overview
Python and PyPI allow developers to distribute code with "entry points". These entry points let users call into python code from the command line, effectively acting like standalone applications.

`pipx` is a tool to install and run any of the thousands of Python applications available on PyPI in a safe, convenient, and reliable way. Not all Python packages have entry points, but many do.

`pipx` lets you:
* Safely install packages to isolated virtual environments, while globally exposing their CLI entry points so you can run them from anywhere (see the `install` command)
* Easily list, upgrade, and uninstall packages that were installed with pipx
* Run the latest version of a CLI application in a temporary environment (see the `run` command)
* Run binaries from the `__pypackages__` directory per PEP 582 as companion tool to [pythonloc](https://github.com/cs01/pythonloc)

Best of all, pipx runs with regular user permissions, never calling `sudo pip install` (you aren't doing that, are you? 😄).

pipx is similar to JavaScript's [npx](https://medium.com/@maybekatz/introducing-npx-an-npm-package-runner-55f7d4bd282b) - which ships with npm, but also allows you to install instead of just run. pipx does not ship with pip but installing it is often an important part of bootstrapping your system.

### Safely installing to isolated environments
You can globally install a CLI application by running
```
pipx install PACKAGE
```

This automatically creates a virtual environment, installs the package, and adds the package's CLI entry points to a location on your `PATH`. For example, `pipx install pycowsay` makes the `pycowsay` command available globally, but sandboxes the pycowsay package in its own virtual environment. **pipx never needs to run as sudo to do this.**

Example:
```
>> pipx install pycowsay
  installed package pycowsay 2.0, Python 3.6.7
  These binaries are now globally available
    - pycowsay
done! ✨ 🌟 ✨

>> pipx list
venvs are in /home/user/.local/pipx/venvs
binaries are exposed on your $PATH at /home/user/.local/bin
   package pycowsay 2.0, Python 3.6.7
    - pycowsay

>> pycowsay moooo
  _____
< moooo >
  =====
          \
           \
             ^__^
             (oo)\_______
             (__)\       )\/       ||----w |
                 ||     ||
```

### Running in temporary, sandboxed environments
pipx makes running the latest version of a program in a temporary environment as easy as
```
pipx run BINARY [ARGS...]
```
This will install the package in an isolated, temporary directory and invoke the binary. Try it!

```
pipx run pycowsay moo
```

Notice that you **don't need to execute any install commands to run the binary**.

Re-running the same binary is quick because pipx caches Virtual Environments on a per-binary basis. These caches last two days.

You can run .py files directly, too.
```
pipx run https://gist.githubusercontent.com/cs01/fa721a17a326e551ede048c5088f9e0f/raw/6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py
pipx is working!
```

## Testimonials

"Thanks for improving the workflow that pipsi has covered in the past. Nicely done!"
— [Jannis Leidel](https://twitter.com/jezdez) PSF fellow and former pip maintainer

"Just the “pipx upgrade-all” command is already a huge win over pipsi"
— [Stefane Fermigier](https://twitter.com/sfermigier/status/1093073303521116160)

"This tool filled in the gap that was missing with pipenv and Virtual Environmentwrapper."
— [Mason Egger](https://medium.com/homeaway-tech-blog/simplify-your-python-developer-environment-aba90f32dddb)


### System Requirements
python 3.6+ is required to install pipx. pipx can run binaries from packages with Python 3.3+. Don't have Python 3.6 or later? See [Python 3 Installation & Setup Guide](https://realpython.com/installing-python/).

pipx works on macOS, linux, and Windows.

## Install pipx
```
pip install --user pipx
pipx ensurepath
```

to be sure you are using python3 you can run

```
python3 -m pip install --user pipx
pipx ensurepath
```

### Using Development Versions
New versions of pipx are published as beta or release candidates. These versions look something like `0.13.0b1`, where `b1` signifies the first beta release of version 0.13. These releases can be tested with
```
pip install --user pipx --upgrade --dev
```
Development occurs on the `dev` branch of this repository. If there is no such branch, that means there is no work currently in development for a new version.


## Usage

```
pipx --help
usage: pipx [-h] [--version]
            {install,inject,upgrade,upgrade-all,uninstall,uninstall-all,reinstall-all,list,run,runpip,ensurepath}
            ...

Install and execute binaries from Python packages.

Binaries can either be installed globally into isolated Virtual Environments
or run directly in an temporary Virtual Environment.

Virtual Envrionment location is /home/$USER/.local/pipx/venvs.
Symlinks to binaries are placed in /home/$USER/.local/bin.
These locations can be overridden with the environment variables
PIPX_HOME and PIPX_BIN_DIR, respectively. (Virtual Environments will
be installed to $PIPX_HOME/venvs)

optional arguments:
  -h, --help            show this help message and exit
  --version             Print version and exit

subcommands:
  Get help for commands with pipx COMMAND --help

  {install,inject,upgrade,upgrade-all,uninstall,uninstall-all,reinstall-all,list,run,runpip,ensurepath}
    install             Install a package
    inject              Install packages into an existing Virtual Environment
    upgrade             Upgrade a package
    upgrade-all         Upgrade all packages. Runs `pip install -U <pkgname>`
                        for each package.
    uninstall           Uninstall a package
    uninstall-all       Uninstall all packages
    reinstall-all       Reinstall all packages with a different Python
                        executable
    list                List installed packages
    run                 Either download the latest version of a package to
                        temporary directory, then run a binary from it, or
                        invoke binary from local `__pypackages__` directory
                        (expiremental, see https://github.com/cs01/pythonloc)
    runpip              Run pip in an existing pipx-managed Virtual
                        Environment
    ensurepath          Ensure /home/$USER/.local/bin is on your PATH
                        environment variable by modifying your shell's
                        configuration file.

```


### pipx install

```
pipx install --help
usage: pipx install [-h] [--spec SPEC] [--include-deps] [--verbose] [--force]
                    [--python PYTHON] [--system-site-packages]
                    [--index-url INDEX_URL] [--editable] [--pip-args PIP_ARGS]
                    package

The install command is the preferred way to globally install binaries
from python packages on your system. It creates an isolated virtual
environment for the package, then ensures the package's binaries are
accessible on your $PATH.

The result: binaries you can run from anywhere, located in packages
you can cleanly upgrade or uninstall. Guaranteed to not have
dependency version conflicts or interfere with your OS's python
packages. 'sudo' is not required to do this.

pipx install PACKAGE
pipx install --python PYTHON PACKAGE
pipx install --spec VCS_URL PACKAGE
pipx install --spec ZIP_FILE PACKAGE
pipx install --spec TAR_GZ_FILE PACKAGE

The argument to `--spec` is passed directly to `pip install`.

The default virtual environment location is /home/$USER/.local/pipx
and can be overridden by setting the environment variable `PIPX_HOME`
 (Virtual Environments will be installed to `$PIPX_HOME/venvs`).

The default binary location is /home/$USER/.local/bin and can be
overridden by setting the environment variable `PIPX_BIN_DIR`.

positional arguments:
  package               package name

optional arguments:
  -h, --help            show this help message and exit
  --spec SPEC           The package name or specific installation source
                        passed to pip. Runs `pip install -U SPEC`. For example
                        `--spec mypackage==2.0.0` or `--spec
                        git+https://github.com/user/repo.git@branch`
  --include-deps        Include binaries of dependent packages
  --verbose
  --force               Install even when the package has already been
                        installed
  --python PYTHON       The Python executable used to create the Virtual
                        Environment and run the associated binary/binaries.
                        Must be v3.3+.
  --system-site-packages
                        Give the virtual environment access to the system
                        site-packages dir.
  --index-url INDEX_URL, -i INDEX_URL
                        Base URL of Python Package Index
  --editable, -e        Install a project in editable mode
  --pip-args PIP_ARGS   Arbitrary pip arguments to pass directly to pip
                        install/upgrade commands

```


#### `pipx install` examples
```
pipx install pycowsay
pipx install --python python3.6 pycowsay
pipx install --python python3.7 pycowsay
pipx install --spec git+https://github.com/ambv/black black
pipx --spec git+https://github.com/ambv/black.git@branch-name black
pipx --spec git+https://github.com/ambv/black.git@git-hash black
pipx install --spec https://github.com/ambv/black/archive/18.9b0.zip black
pipx install --spec black[d] black
pipx install --include-deps jupyter
```

### pipx run

```
pipx run --help
usage: pipx run [-h] [--no-cache] [--pypackages] [--spec SPEC] [--verbose]
                [--python PYTHON] [--system-site-packages]
                [--index-url INDEX_URL] [--editable] [--pip-args PIP_ARGS]
                binary [binary_args [binary_args ...]]

Either download the latest version of a package to temporary directory
then run a binary from it, or invoke a binary from local `__pypackages__`
directory.

If running from a temporary environment, the environment will be cached
and re-used for up to 2 days. This
means subsequent calls to 'run' for the same package will be faster
since they can re-use the cached Virtual Environment.

In support of PEP 582 'run' will use binaries found in a local __pypackages__
 directory, if present. Please note that this behavior is experimental,
 and is a acts as a companion tool to pythonloc. It may be modified or
 removed in the future.

positional arguments:
  binary                binary/package name
  binary_args           arguments passed to the binary when it is invoked

optional arguments:
  -h, --help            show this help message and exit
  --no-cache            Do not re-use cached virtual environment if it exists
  --pypackages          Require binary to be run from local __pypackages__
                        directory
  --spec SPEC           The package name or specific installation source
                        passed to pip. Runs `pip install -U SPEC`. For example
                        `--spec mypackage==2.0.0` or `--spec
                        git+https://github.com/user/repo.git@branch`
  --verbose
  --python PYTHON       The Python version to run package's CLI binary with.
                        Must be v3.3+.
  --system-site-packages
                        Give the virtual environment access to the system
                        site-packages dir.
  --index-url INDEX_URL, -i INDEX_URL
                        Base URL of Python Package Index
  --editable, -e        Install a project in editable mode
  --pip-args PIP_ARGS   Arbitrary pip arguments to pass directly to pip
                        install/upgrade commands

```


#### `pipx run` examples

pipx enables you to test various combinations of Python versions and package versions in ephemeral environments:
```
pipx run BINARY  # latest version of binary is run with python3
pipx --spec PACKAGE==2.0.0 run BINARY  # specific version of package is run
pipx --python 3.4 run BINARY  # Installed and invoked with specific Python version
pipx --python 3.7 --spec PACKAGE=1.7.3 run BINARY
pipx --spec git+https://url.git run BINARY  # latest version on master is run
pipx --spec git+https://url.git@branch run BINARY
pipx --spec git+https://url.git@hash run BINARY
pipx run pycowsay moo
pipx --version  # prints pipx version
pipx run pycowsay  --version  # prints pycowsay version
pipx --python pythonX pycowsay
pipx --spec pycowsay==2.0 pycowsay --version
pipx --spec git+https://github.com/ambv/black.git black
pipx --spec git+https://github.com/ambv/black.git@branch-name black
pipx --spec git+https://github.com/ambv/black.git@git-hash black
pipx --spec https://github.com/ambv/black/archive/18.9b0.zip black --help
pipx https://gist.githubusercontent.com/cs01/fa721a17a326e551ede048c5088f9e0f/raw/6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py
```


### pipx upgrade

```
pipx upgrade --help
usage: pipx upgrade [-h] [--spec SPEC] [--include-deps]
                    [--system-site-packages] [--index-url INDEX_URL]
                    [--editable] [--pip-args PIP_ARGS] [--verbose]
                    package

Upgrade a package in a pipx-managed Virtual Environment by running 'pip
install --upgrade PACKAGE'

positional arguments:
  package

optional arguments:
  -h, --help            show this help message and exit
  --spec SPEC           The package name or specific installation source
                        passed to pip. Runs `pip install -U SPEC`. For example
                        `--spec mypackage==2.0.0` or `--spec
                        git+https://github.com/user/repo.git@branch`
  --include-deps        Include binaries of dependent packages
  --system-site-packages
                        Give the virtual environment access to the system
                        site-packages dir.
  --index-url INDEX_URL, -i INDEX_URL
                        Base URL of Python Package Index
  --editable, -e        Install a project in editable mode
  --pip-args PIP_ARGS   Arbitrary pip arguments to pass directly to pip
                        install/upgrade commands
  --verbose

```


### pipx upgrade-all

```
pipx upgrade-all --help
usage: pipx upgrade-all [-h] [--include-deps] [--system-site-packages]
                        [--index-url INDEX_URL] [--editable]
                        [--pip-args PIP_ARGS] [--skip SKIP [SKIP ...]]
                        [--verbose]

Upgrades all packages within their virtual environments by running 'pip
install --upgrade PACKAGE'

optional arguments:
  -h, --help            show this help message and exit
  --include-deps        Include binaries of dependent packages
  --system-site-packages
                        Give the virtual environment access to the system
                        site-packages dir.
  --index-url INDEX_URL, -i INDEX_URL
                        Base URL of Python Package Index
  --editable, -e        Install a project in editable mode
  --pip-args PIP_ARGS   Arbitrary pip arguments to pass directly to pip
                        install/upgrade commands
  --skip SKIP [SKIP ...]
                        skip these packages
  --verbose

```


### pipx inject

```
pipx inject --help
usage: pipx inject [-h] [--include-binaries] [--include-deps]
                   [--system-site-packages] [--index-url INDEX_URL]
                   [--editable] [--pip-args PIP_ARGS] [--verbose]
                   package dependencies [dependencies ...]

Installs packages to an existing pipx-managed virtual environment.

positional arguments:
  package               Name of the existing pipx-managed Virtual Environment
                        to inject into
  dependencies          the packages to inject into the Virtual Environment

optional arguments:
  -h, --help            show this help message and exit
  --include-binaries    Add binaries from the injected packages onto your PATH
  --include-deps        Include binaries of dependent packages
  --system-site-packages
                        Give the virtual environment access to the system
                        site-packages dir.
  --index-url INDEX_URL, -i INDEX_URL
                        Base URL of Python Package Index
  --editable, -e        Install a project in editable mode
  --pip-args PIP_ARGS   Arbitrary pip arguments to pass directly to pip
                        install/upgrade commands
  --verbose

```


#### `pipx inject` example

One use of the inject command is setting up a REPL with some useful extra packages.

```
pipx install ptpython
pipx inject ptpython requests pendulum
```

After running the above commands, you will be able to import and use the `requests` and `pendulum` packages inside a `ptpython` repl.

### pipx uninstall

```
pipx uninstall --help
usage: pipx uninstall [-h] [--verbose] package

Uninstalls a pipx-managed Virtual Envrionment by deleting it and any files
that point to its binaries.

positional arguments:
  package

optional arguments:
  -h, --help  show this help message and exit
  --verbose

```


### pipx uninstall-all

```
pipx uninstall-all --help
usage: pipx uninstall-all [-h] [--verbose]

Uninstall all pipx-managed packages

optional arguments:
  -h, --help  show this help message and exit
  --verbose

```


### pipx reinstall-all

```
pipx reinstall-all --help
usage: pipx reinstall-all [-h] [--include-deps] [--system-site-packages]
                          [--index-url INDEX_URL] [--editable]
                          [--pip-args PIP_ARGS] [--skip SKIP [SKIP ...]]
                          [--verbose]
                          python

Reinstalls all packages using a different version of Python.

Packages are uninstalled, then installed with pipx install PACKAGE.
This is useful if you upgraded to a new version of Python and want
all your packages to use the latest as well.

If you originally installed a package from a source other than PyPI,
this command may behave in unexpected ways since it will reinstall from PyPI.

positional arguments:
  python

optional arguments:
  -h, --help            show this help message and exit
  --include-deps        Include binaries of dependent packages
  --system-site-packages
                        Give the virtual environment access to the system
                        site-packages dir.
  --index-url INDEX_URL, -i INDEX_URL
                        Base URL of Python Package Index
  --editable, -e        Install a project in editable mode
  --pip-args PIP_ARGS   Arbitrary pip arguments to pass directly to pip
                        install/upgrade commands
  --skip SKIP [SKIP ...]
                        skip these packages
  --verbose

```


### pipx list

```
pipx list --help
usage: pipx list [-h] [--verbose]

List packages and binariess installed with pipx

optional arguments:
  -h, --help  show this help message and exit
  --verbose

```


#### `pipx list` example
```
> pipx list
venvs are in /Users/user/.local/pipx/venvs
binaries are exposed on your $PATH at /Users/user/.local/bin
   package black 18.9b0, Python 3.7.0
    - black
    - blackd
   package pipx 0.10.0, Python 3.7.0
    - pipx
```

### pipx runpip

```
pipx runpip --help
usage: pipx runpip [-h] [--verbose] package [pipargs [pipargs ...]]

Run pip in an existing pipx-managed Virtual Environment

positional arguments:
  package     Name of the existing pipx-managed Virtual Environment to run pip
              in
  pipargs     Arguments to forward to pip command

optional arguments:
  -h, --help  show this help message and exit
  --verbose

```



### pipx ensurepath

```
pipx ensurepath --help
usage: pipx ensurepath [-h] [--force]

Ensure /home/$USER/.local/bin is on your PATH environment variable by
modifying your shell's configuration file. This only needs to be run once
after initial installation if /home/$USER/.local/bin is not already on your
PATH.

optional arguments:
  -h, --help  show this help message and exit
  --force     Add text to your shell's config file even if it looks like your
              PATH already has /home/$USER/.local/bin

```


#### `pipx ensurepath` example
```
> pipx ensurepath
Added /home/user/.local/bin to the PATH environment variable in /home/user/.bashrc

Open a new terminal to use pipx ✨ 🌟 ✨
```
```
> pipx ensurepath
Your PATH looks like it already is set up for pipx. Pass `--force` to modify the PATH.
```
## Programs to try with pipx
Here are some programs you can try out. If you've never used the program before, make sure you add the `--help` flag so it doesn't do something you don't expect. If you decide you want to install, you can run `pipx install PACKAGE` instead.
```
pipx install ansible  # IT automation
pipx run asciinema  # Record and share your terminal sessions, the right way.
pipx run black  # uncompromising Python code formatter
pipx --spec babel run pybabel  # internationalizing and localizing Python applications
pipx --spec chardet run chardetect  # detect file encoding
pipx run cookiecutter  # creates projects from project templates
pipx run create-python-package  # easily create and publish new Python packages
pipx run flake8  # tool for style guide enforcement
pipx run gdbgui  # browser-based gdb debugger
pipx run hexsticker  # create hexagon stickers automatically
pipx run ipython  # powerful interactive Python shell
pipx run jupyter  # web-based notebook environment for interactive computing
pipx run pipenv  # python dependency/environment management
pipx run poetry  # python dependency/environment/packaging management
pipx run pylint  # source code analyzer
pipx run pyinstaller  # bundles a Python application and all its dependencies into a single package
pipx run pyxtermjs  # fully functional terminal in the browser  
pipx install shell-functools  # Functional programming tools for the shell
```

## How it Works
When installing a package and its binaries (`pipx install package`) pipx will
* create directory ~/.local/pipx/venvs/PACKAGE
* create a Virtual Environment in ~/.local/pipx/venvs/PACKAGE
* update the Virtual Environment's pip to the latest version
* install the desired package in the Virtual Environment
* exposes binaries at `~/.local/bin` that point to new binaries in `~/.local/pipx/venvs/PACKAGE/bin` (such as `~/.local/bin/black` -> `~/.local/pipx/venvs/black/bin/black`)
* As long as `~/.local/bin/` is on your PATH, you can now invoke the new binaries globally

When running a binary (`pipx run BINARY`), pipx will
* Create a temporary directory (or reuse a cached virtual environment for this package) with a name based on a hash of the attributes that make the run reproducible. This includes things like the package name, spec, python version, and pip arguments.
* create a Virtual Environment inside it with `python -m venv`
* update pip to the latest version
* install the desired package in the Virtual Environment
* invoke the binary


These are all things you can do yourself, but pipx automates them for you. If you are curious as to what pipx is doing behind the scenes, you can always pass the `--verbose` flag to see every single command and argument being run.

## Contributing
To develop `pipx` first clone the repository, then create and activate a virtual environment.
```
python3 -m venv venv
source venv/bin/activate
```
Next install pipx in "editable mode".
```
pip install -e .
```
Now make your changes and run `pipx` as you normally would. Your changes will be used as soon as they are saved.

Make sure your changes pass tests by installing development dependencies
```
pip install -e .[dev]
```
then running tests
```
python setup.py test
```
If you added or modified any command line argument parsers, be sure to regenerate the README.md.
```
make docs
```

When finished, you can exit the virtual environment by running `deactivate` and remove the virtual environment with `rm -r venv`.

## How does this compare to pipsi?
* pipx is under active development. pipsi is no longer maintained.
* pipx and pipsi both install packages in a similar way
* pipx always makes sure you're using the latest version of pip
* pipx has the ability to run a binary in one line, leaving your system unchanged after it finishes (`pipx run BINARY`) where pipsi does not
* pipx has the ability to recursively install binaries from dependent packages
* pipx adds more useful information to its output
* pipx has more CLI options such as upgrade-all, reinstall-all, uninstall-all
* pipx is more modern. It uses Python 3.6+, and the `venv` package in the Python3 standard library instead of the python 2 package `virtualenv`.
* pipx works with Python homebrew installations while pipsi does not (at least on my machine)
* pipx defaults to less verbose output
* pipx allows you to see each command it runs by passing the --verbose flag
* pipx prints emojies 😀

## Migrating to pipx from pipsi
Although `pipx` does not provide an automatic migration command,
it is pretty easy to do it from the command-line:

```bash
# install pipx with the recommended method
pip install --user pipx
pipx ensurepath
# you may have to open a new terminal here for pipx to be on your PATH

# migrate from pipsi to pipx
pipsi list | grep 'Package ' | cut -d\" -f2 | \
  while read -r p; do
    pipsi uninstall --yes "$p"
    # reinstall everything with python 3.6
    pipx install --python python3.6 "$p"
  done

# clean up
rm -rf ~/.local/pipsi
rm ~/.local/bin/pipsi
```

If you want to do this manually, you will have to remove pipsi's directory completely then reinstall everything with pipx.

First remove pipsi's directory (this is its default)
```
rm -r ~/.local/pipsi
```

There will still be files in `~/.local/bin` that point to `~/.local/pipsi/venvs`. If you reinstall the same packages with `pipx`, the files will be overwritten with valid files that point to the new pipx directory in `~/.local/pipx/venvs`. You may also want to remove files in `~/.local/bin`, but be sure the files you delete there were created by pipsi.

## How does this compare with `pip-run`?
[pip-run](https://github.com/jaraco/pip-run) is focused on running **arbitrary Python code in ephemeral environments** while pipx is focused on running **Python binaries in ephemeral and non-ephemeral environments**.

For example these two commands both install poetry to an ephemeral environment and invoke poetry with `--help`.
```
pipx run poetry --help
pip-run poetry -- -m poetry --help
```

## [Changelog](https://github.com/pipxproject/pipx/blob/master/CHANGELOG.md)

## Credits
pipx was inspired by [pipsi](https://github.com/mitsuhiko/pipsi) and [npx](https://github.com/zkat/npx).

* [Chad Smith](https://github.com/cs01/), creator and maintainer
* [Bjorn Neergaard](https://github.com/neersighted), contributor
* [Diego Fernandez](https://github.com/aiguofer), contributor
* [tkossak](https://github.com/tkossak), contributor
* [Shawn Hensley](https://github.com/sahensley), contributor