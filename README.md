# pipx: execute binaries from Python packages in isolated environments

<p align="center">
<a href="https://github.com/cs01/pipx/raw/master/pipx_demo.gif">
<img src="https://github.com/cs01/pipx/raw/master/pipx_demo.gif">
</a>

</p>

<a href="https://github.com/ambv/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>

*pipx is still a new project. Please submit issues if you have questions or bugs to report. For comparison to pipsi, see [how does this compare to pipsi?](#how-does-this-compare-to-pipsi) Read more about pipx on the [blog post](https://medium.com/@grassfedcode/bringing-some-of-javascripts-packaging-solutions-to-python-1b02430d589e).*

*pipx uses the word "binary" to describe a file that can be run directly from the command line. These files are located in the `bin` directory of a Python installation, alongside other executables. Despite the name, they usually do not contain binary data.*

pipx makes running the latest version of a program as easy as
```
> pipx BINARY
```
This will install the package in a temporary directory, invoke the binary, then clean up after itself, leaving your system untouched. Try it! `pipx cowsay moo`. Notice that you **don't need to execute any install commands to run the binary**.

It also makes (safely) installing a program globally as easy as
```
> pipx install PACKAGE
```
For example, `pipx install cowsay`. It eliminates the tedium of creating and removing virtualenvs, and removes the temptation to run `sudo pip install ...` (you aren't doing that, are you? 😄).

pipx combines the features of JavaScript's [npx](https://medium.com/@maybekatz/introducing-npx-an-npm-package-runner-55f7d4bd282b) - which ships with npm - and Python's [pipsi](https://github.com/mitsuhiko/pipsi). pipx does not ship with pip but I consider it to be an important part of bootstrapping your system, similar to how the npm team bootstraps npm with npx.

## testimonials
@tkossak
> Thank you! Great tool btw. I already use it instead of pipsi :)

## install pipx
```
curl https://raw.githubusercontent.com/cs01/pipx/master/get-pipx.py | python3
```
python 3.6+ is required to install pipx. Binaries can be run with Python 3.3+. If python3 is not found on your PATH or the full path to python3 is not specified, curl will fail with the error message: "(23) Failed writing body."

To upgrade
```
pipx upgrade pipx
```

To uninstall
```
pipx uninstall pipx
```

## usage
```
pipx BINARY
```

```
pipx [--spec PACKAGE] [--python PYTHON] BINARY [ARGS...]
```

```
pipx {install,upgrade,upgrade-all,uninstall,uninstall-all,list} [--help]
```

## pipx commands
`pipx` can be invoked to directly run a binary (`pipx BINARY`) or to run a pipx command (`pipx COMMAND`). The commands are
```
install, upgrade, upgrade-all, uninstall, uninstall-all, reinstall-all, list
```
You can run `pipx COMMAND --help` for details on each command. You cannot run a binary with the same name as a pipx command.

### run a binary
```
pipx BINARY
pipx [--python PYTHON] [--spec SPEC] BINARY [ARGS...]
```

#### examples
pipx enables you to test various combinations of Python versions and package versions in ephemeral environments:
```
pipx BINARY  # latest version of binary is run with python3
pipx --spec PACKAGE==2.0.0 BINARY  # specific version of package is run
pipx --python 3.4 BINARY  # Installed and invoked with specific Python version
pipx --python 3.7 --spec PACKAGE=1.7.3 BINARY
pipx --spec git+https://url.git BINARY  # latest version on master is run
pipx --spec git+https://url.git@branch BINARY
pipx --spec git+https://url.git@hash BINARY
pipx cowsay moo
pipx --version cowsay  # prints pipx version
pipx cowsay  --version  # prints cowsay version
pipx --python pythonX cowsay
pipx --spec cowsay==2.0 cowsay --version
pipx --spec git+https://github.com/ambv/black.git black
pipx --spec git+https://github.com/ambv/black.git@branch-name black
pipx --spec git+https://github.com/ambv/black.git@git-hash black
pipx --spec https://github.com/ambv/black/archive/18.9b0.zip black --help
pipx https://gist.githubusercontent.com/cs01/fa721a17a326e551ede048c5088f9e0f/raw/6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py
```

### install a package and expose binaries globally
The install command is the preferred way to globally install binaries from python packages on your system. It creates an isolated virtual environment for the package, then in a folder on your PATH creates symlinks to all the binaries provided by the installed package. It does not link to the package's dependencies.

*Note: pipx determines a package's binaries (also known as entry points, console scripts, or scripts) by inspecting metadata about the package. Sometimes a package is built in such a way that pipx cannot determine its binaries. In such cases, please create an issue.*

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

#### install examples
All of the examples in the `run a binary` section can be used by changing `pipx` to `pipx install`.

### upgrade
```
pipx upgrade PACKAGE
```

### upgrade all packages
```
pipx upgrade-all
```

### uninstall
```
pipx uninstall PACKAGE
```
### uninstall all packages (including pipx)
```
pipx uninstall-all
```

### reinstall all packages using a different version of Python
```
pipx reinstall-all PYTHON
```
Specify a version of Python to associate all installed packages with. Packages are uninstalled, then installed with `pip install PACKAGE`. This is useful if you upgraded to a new version of Python and want all your packages to use the latest as well.

If you originally installed a package from a source other than PyPI, this command may behave in unexpected ways since it will reinstall from PyPI.

### list installed packages/binaries
```
pipx list
```
results in something like
```
venvs are in /Users/user/.local/pipx/venvs
symlinks to binaries are in /Users/user/.local/bin
  package: black, 18.9b0
    - black
    - blackd
  package: pipx, 0.0.0.11
    - pipx
```

## walkthrough
I'll use the python package `black` as an example. The `black` package ships with a binary called black. You can run it with pipx just like this.
```
> pipx black --help
Usage: black [OPTIONS] [SRC]...

  The uncompromising code formatter.
  ...
```
Black just ran, but you didn't have to run `venv` or install commands. How easy was that!?

pipx makes safely installing the program to globally accessible, isolated environment as easy as
```
> pipx install black
```
so now `black` will be available globally, wherever you want to use it, but **not mixed in with your OS's Python packages**.
```
> black --help  # now available globally
Usage: black [OPTIONS] [SRC]...

  The uncompromising code formatter.
  ...
```

> Aside: I just want to take a second to note how different this is from using `sudo pip install ...` (which you should NEVER do). Using `sudo pip install ...` will mix Python packages installed and required by your OS with whatever you just installed. This can result in very bad things happening. And since all the dependencies were installed along with it (which you have no idea what they were), you can't easily uninstall them -- you have to know every single one and run `sudo pip uninstall ...` for them!

You can uninstall packages with
```
pipx uninstall black
```
This uninstalls the black package **and all of its dependencies**, but doesn't affect any other packages or binaries.

Oh one other thing. You can also run Python programs directly from a URL, such as github gists. Behold [this gist](https://gist.github.com/cs01/fa721a17a326e551ede048c5088f9e0f) run directly with pipx:
```
> pipx https://gist.githubusercontent.com/cs01/fa721a17a326e551ede048c5088f9e0f/raw/6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py
pipx is working!
```

## programs to try with pipx
Here are some programs you can try out with no obligation. If you've never used the program before, make sure you add the `--help` flag so it doesn't do something you don't expect. If you decide you want to install, you can run `pipx install PACKAGE` instead.
```
pipx asciinema  # Record and share your terminal sessions, the right way.
pipx black  # uncompromising Python code formatter
pipx --spec babel pybabel  # internationalizing and localizing Python applications
pipx --spec chardet chardetect  # detect file encoding
pipx cookiecutter  # creates projects from project templates
pipx create-python-package  # easily create and publish new Python packages
pipx flake8  # tool for style guide enforcement
pipx gdbgui  # browser-based gdb debugger
pipx hexsticker  # create hexagon stickers automatically
pipx ipython  # powerful interactive Python shell
pipx pipenv  # python dependency/environment management
pipx poetry  # python dependency/environment/packaging management
pipx pylint  # source code analyzer
pipx pyinstaller  # bundles a Python application and all its dependencies into a single package
pipx pyxtermjs  # fully functional terminal in the browser  
```

## how it works
When running a binary (`pipx BINARY`), pipx will
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

## how does this compare to pipsi?
* pipx is under active development. pipsi is no longer maintained.
* pipx and pipsi both install packages in a similar way, but pipx always makes sure you're using the lastest version of pip
* pipx has the ability to run a binary in one line, leaving your system unchanged after it finishes (`pipx binary`) where pipsi does not
* pipx adds more useful information to its output
* pipx has more CLI options such as upgrade-all, reinstall-all, uninstall-all
* pipx is more modern. It uses Python 3.6+, and venv instead of virtualenv.
* pipx always uses the lastest version of pip in its venvs
* pipx works with Python homebrew installations while pipsi does not (at least on my machine)
* pipx defaults to less verbose output
* pipx allows you to see each command it runs by passing the --verbose flag
* pipx prints emojies 😀

## how does this compare with rwt?
[run with this](https://github.com/jaraco/rwt) is focused on running **arbitrary Python code in ephemeral environments** while pipx is focused on running **Python binaries in ephemeral and non-ephemeral environments**.

For example these two commands both install poetry to an ephemeral environment and invoke poetry with `--help`.
```
pipx poetry --help
rwt poetry -- -m poetry --help
```

## credits
pipx was inspired by [pipsi](https://github.com/mitsuhiko/pipsi) and [npx](https://github.com/zkat/npx).
