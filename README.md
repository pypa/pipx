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
<img src="https://img.shields.io/badge/pypi-0.12.0.1-blue.svg" /></a>
<a href="https://github.com/ambv/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

*For comparison to pipsi, see [how does this compare to pipsi?](#how-does-this-compare-to-pipsi) and [migrating to pipx from pipsi](#migrating-to-pipx-from-pipsi).*

*pipx uses the word "binary" to describe a CLI application that can be run directly from the command line. These files are located in the `bin` directory of a Python installation, alongside other executables. Despite the name, they do not necessarily contain binary data.*

## Overview
* Safely install packages to isolated virtual environments, while globally exposing their CLI applications so you can run them from anywhere
* Easily list, upgrade, and uninstall packages that were installed with pipx
* Run the latest version of a CLI application from a package in a temporary virtual environment, leaving your system untouched after it finishes
* Runs with regular user permissions, never calling `sudo pip install ...` (you aren't doing that, are you? 😄).

pipx combines the features of JavaScript's [npx](https://medium.com/@maybekatz/introducing-npx-an-npm-package-runner-55f7d4bd282b) - which ships with npm - and Python's [pipsi](https://github.com/mitsuhiko/pipsi). pipx does not ship with pip but it is an important part of bootstrapping your system.

### Safely installing to isolated environments
You can globally install a CLI application by running
```
pipx install PACKAGE
```

This automatically creates a virtual environment, installs the package, and symlinks the package's CLI binaries to a location on your `PATH`. For example, `pipx install cowsay` makes the `cowsay` command available globally, but sandboxes the cowsay package in its own virtual environment. **pipx never needs to run as sudo to do this.**

Example:
```
>> pipx install cowsay
  installed package cowsay 2.0, Python 3.6.7
  These binaries are now globally available
    - cowsay
done! ✨ 🌟 ✨

>> cowsay moooo
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

### Running in one-time ephemeral environments
pipx makes running the latest version of a program in a one-time environment as easy as
```
pipx run BINARY [ARGS...]
```
This will install the package in a temporary directory, invoke the binary, then clean up after itself, leaving your system untouched. Try it!

```
pipx run cowsay moo
```

Notice that you **don't need to execute any install commands to run the binary**.

You can run .py files directly, too.
```
pipx run https://gist.githubusercontent.com/cs01/fa721a17a326e551ede048c5088f9e0f/raw/6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py
pipx is working!
```

## Testimonials

"Just the “pipx upgrade-all” command is already a huge win over pipsi"
— [Stefane Fermigier](https://twitter.com/sfermigier/status/1093073303521116160)

"This tool filled in the gap that was missing with pipenv and virtualenvwrapper."
— [Mason Egger](https://medium.com/homeaway-tech-blog/simplify-your-python-developer-environment-aba90f32dddb)

"Thank you! Great tool btw. I already use it instead of pipsi :)"
— @tkossak


### System Requirements
python 3.6+ is required to install pipx. pipx can run binaries from packages with Python 3.3+. Don't have Python 3.6 or later? See [Python 3 Installation & Setup Guide](https://realpython.com/installing-python/).

pipx works on macOS, linux, and Windows.

## Install `pipx`
```
pip install --user pipx
pipx ensurepath
```

to be sure you are using python3 you can run

```
python3 -m pip install --user pipx
pipx ensurepath
```

## Usage

```
pipx {install,inject,upgrade,upgrade-all,uninstall,uninstall-all,reinstall-all,list,run}
```

You can run `pipx COMMAND --help` for details on each command.

### Install a Package
The install command is the preferred way to globally install binaries from python packages on your system. It creates an isolated virtual environment for the package, then in a folder on your PATH creates symlinks to all the binaries provided by the installed package. It does not link to the package's dependencies.

The result: binaries you can run from anywhere, located in packages you can **cleanly** upgrade or uninstall. Guaranteed to not have dependency version conflicts or interfere with your OS's python packages. All **without** running `sudo`.
```
pipx install PACKAGE
pipx install --python PYTHON PACKAGE
pipx install --spec VCS_URL PACKAGE
pipx install --spec ZIP_FILE PACKAGE
pipx install --spec TAR_GZ_FILE PACKAGE
```

The argument to `--spec` is passed directly to `pip install`.

The default virtual environment location is `~/.local/pipx/venvs` and can be overridden by setting the environment variable `PIPX_HOME`.

The default binary location is `~/.local/bin` and can be overridden by setting the environment variable `PIPX_BIN_DIR`.

#### Package Installation Examples
```
pipx install cowsay
pipx install --python python3.6 cowsay
pipx install --python python3.7 cowsay
pipx install --spec git+https://github.com/ambv/black black
pipx --spec git+https://github.com/ambv/black.git@branch-name black
pipx --spec git+https://github.com/ambv/black.git@git-hash black
pipx install --spec https://github.com/ambv/black/archive/18.9b0.zip black
pipx install --spec black[d] black
```

### `upgrade`
Upgrades a package within its virtual environments by running `pip install --upgrade PACKAGE`.

```
pipx upgrade PACKAGE
```

### `upgrade-all`
Upgrades all packages within their virtual environments by running `pip install --upgrade PACKAGE`.
```
pipx upgrade-all
```

### `inject`
Adds packages to an existing pipx-managed virtual environment.

```
pipx inject PACKAGE DEPENDENCIES
```

#### Inject Example

One use of the inject command is setting up a REPL with some useful extra packages.

```
pipx install ptpython
pipx inject ptpython requests pendulum
```

After running the above commands, you will be able to import and use the `requests` and `pendulum` packages inside a `ptpython` repl.

### `uninstall`
Uninstalls a package by deleting its virtual environment and any symlinks that point to its binaries.
```
pipx uninstall PACKAGE
```
### `uninstall-all`
Uninstalls all packages (including pipx)
```
pipx uninstall-all
```

### `reinstall-all`
Reinstalls all packages using a different version of Python.
```
pipx reinstall-all PYTHON
```
Specify a version of Python to associate all installed packages with. Packages are uninstalled, then installed with `pip install PACKAGE`. This is useful if you upgraded to a new version of Python and want all your packages to use the latest as well.

If you originally installed a package from a source other than PyPI, this command may behave in unexpected ways since it will reinstall from PyPI.

### `list`
Lists installed packages/binaries
```
pipx list
```
results in something like
```
venvs are in /Users/user/.local/pipx/venvs
symlinks to binaries are in /Users/user/.local/bin
   package black 18.9b0, Python 3.7.0
    - black
    - blackd
   package pipx 0.10.0, Python 3.7.0
    - pipx
```
### `run`
Run a binary from the latest version of its package in a temporary, ephemeral environment.
```
pipx run BINARY
pipx [--python PYTHON] [--spec SPEC] BINARY [ARGS...]
```

#### `pipx run` Examples
pipx enables you to test various combinations of Python versions and package versions in ephemeral environments:
```
pipx run BINARY  # latest version of binary is run with python3
pipx --spec PACKAGE==2.0.0 run BINARY  # specific version of package is run
pipx --python 3.4 run BINARY  # Installed and invoked with specific Python version
pipx --python 3.7 --spec PACKAGE=1.7.3 run BINARY
pipx --spec git+https://url.git run BINARY  # latest version on master is run
pipx --spec git+https://url.git@branch run BINARY
pipx --spec git+https://url.git@hash run BINARY
pipx run cowsay moo
pipx --version  # prints pipx version
pipx run cowsay  --version  # prints cowsay version
pipx --python pythonX cowsay
pipx --spec cowsay==2.0 cowsay --version
pipx --spec git+https://github.com/ambv/black.git black
pipx --spec git+https://github.com/ambv/black.git@branch-name black
pipx --spec git+https://github.com/ambv/black.git@git-hash black
pipx --spec https://github.com/ambv/black/archive/18.9b0.zip black --help
pipx https://gist.githubusercontent.com/cs01/fa721a17a326e551ede048c5088f9e0f/raw/6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py
```

## Walkthrough
I'll use the python package `black` as an example. The `black` package ships with a binary called black. You can run it with pipx just like this.
```
pipx run black --help
Usage: black [OPTIONS] [SRC]...

  The uncompromising code formatter.
  ...
```
Black just ran, but you didn't have to run `venv` or install commands. How easy was that!?

pipx makes safely installing the program to globally accessible, isolated environment as easy as
```
pipx install black
```
so now `black` will be available globally, wherever you want to use it, but **not mixed in with your OS's Python packages**.
```
black --help  # now available globally
Usage: black [OPTIONS] [SRC]...

  The uncompromising code formatter.
  ...
```

> Aside: I just want to take a second to note how different this is from using `sudo pip install ...` (which you should NEVER do). Using `sudo pip install ...` will mix Python packages installed and required by your OS with whatever you just installed. This can result in very bad things happening. And since all the dependencies were installed along with it (and you have no idea what they were), you can't easily uninstall them -- you have to know every single one and run `sudo pip uninstall ...` for them!

You can uninstall packages with
```
pipx uninstall black
```
This uninstalls the black package **and all of its dependencies**, but doesn't affect any other packages or binaries.

## Programs to try with pipx
Here are some programs you can try out with no obligation. If you've never used the program before, make sure you add the `--help` flag so it doesn't do something you don't expect. If you decide you want to install, you can run `pipx install PACKAGE` instead.
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
pipx run pipenv  # python dependency/environment management
pipx run poetry  # python dependency/environment/packaging management
pipx run pylint  # source code analyzer
pipx run pyinstaller  # bundles a Python application and all its dependencies into a single package
pipx run pyxtermjs  # fully functional terminal in the browser  
pipx install shell-functools  # Functional programming tools for the shell
```

## How it Works
When running a binary (`pipx run BINARY`), pipx will
* create a temporary directory
* create a virtualenv inside it with `python -m venv`
* update pip to the latest version
* install the desired package in the virtualenv
* invoke the binary
* erase the temporary directory leaving your system untouched

When installing a package and its binaries (`pipx install package`) pipx will
* create directory ~/.local/pipx/venvs/PACKAGE
* create a virtualenv in ~/.local/pipx/venvs/PACKAGE
* update pip to the latest version
* install the desired package in the virtualenv
* create symlinks in ~/.local/bin that point to new binaries in ~/.local/pipx/venvs/PACKAGE/bin (such as ~/.local/bin/black -> ~/.local/pipx/venvs/black/bin/black)
* As long as `~/.local/bin/` is on your PATH, you can now invoke the new binaries globally

These are all things you can do yourself, but pipx automates them for you. If you are curious as to what pipx is doing behind the scenes, you can always use `pipx --verbose ...`.

## Contributing
To develop `pipx` first clone the repository, then create and activate a virtual environment.
```
python3 -m venv pipxvenv
source pipxvenv/bin/activate
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
python test.py
```

When finished, you can exit the virtual environment by running `deactivate` and remove the virtual environment with `rm -r pipxvenv`.

## How does this compare to pipsi?
* pipx is under active development. pipsi is no longer maintained.
* pipx and pipsi both install packages in a similar way
* pipx always makes sure you're using the latest version of pip
* pipx has the ability to run a binary in one line, leaving your system unchanged after it finishes (`pipx run BINARY`) where pipsi does not
* pipx adds more useful information to its output
* pipx has more CLI options such as upgrade-all, reinstall-all, uninstall-all
* pipx is more modern. It uses Python 3.6+, and venv instead of virtualenv.
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

There will still be symlinks in `~/.local/bin` that point to `~/.local/pipsi/venvs`. If you reinstall the same packages with `pipx`, the symlinks will be overwritten with valid symlinks that point to the new pipx directory in `~/.local/pipx/venvs`. You may also want to remove files in `~/.local/bin`, but be sure the files you delete there were created by pipsi.

## How does this compare with `pip-run`?
[run with this](https://github.com/jaraco/pip-run) is focused on running **arbitrary Python code in ephemeral environments** while pipx is focused on running **Python binaries in ephemeral and non-ephemeral environments**.

For example these two commands both install poetry to an ephemeral environment and invoke poetry with `--help`.
```
pipx run poetry --help
pip-run poetry -- -m poetry --help
```

## [Changelog](https://github.com/pipxproject/pipx/blob/master/CHANGELOG.md)

## Credits
pipx was inspired by [pipsi](https://github.com/mitsuhiko/pipsi) and [npx](https://github.com/zkat/npx).

## Authors
pipx was created and is maintained by [Chad Smith](https://github.com/cs01/).

Contributions and feedback from
* [Bjorn Neergaard](https://github.com/neersighted)
* [Diego Fernandez](https://github.com/aiguofer)
* [Shawn Hensley](https://github.com/sahensley)
* [tkossak](https://github.com/tkossak)
