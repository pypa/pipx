## pipx vs pip
* pip is a general Python package installer. It can be used to install libraries or cli applications with entrypoints.
* pipx is a specialized package installer. It can only be used to install packages with cli entrypoints.
* pipx and pip both install packages from PyPI (or locally)
* pipx relies on pip (and venv)
* pipx replaces a subset of pip's functionality; it lets you install cli applications but NOT libraries that you import in your code.
* you can install pipx with pip

Example interaction:
Install pipx with pip: `pip install --user pipx`

## pipx vs poetry and pipenv
* pipx is used solely for application consumption: you install cli apps with it
* pipenv and poetry are cli apps used to develop applications and libraries
* all three tools wrap pip and virtual environments for more convenient workflows

Example interaction:
Install pipenv and poetry with pipx: `pipx install poetry`
Run pipenv or poetry with pipx: `pipx run poetry --help`

## pipx vs venv
* venv is part of Python's standard library in Python 3.2 and above
* venv creates "virtual environments" which are sandboxed python installations
* pipx heavily relies on the venv package

Example interaction:
pipx installs packages to environments created with venv. `pipx install black --verbose`

## pipx vs pyenv
* pyenv manages python versions on your system. It helps you install versions like Python 3.6, 3.7, etc.
* pipx installs packages in virtual environments and exposes their entrypoints on your PATH

Example interaction:
Install a Python interpreter with pyenv, then install a package using pipx and that new interpreter: `pipx install black --python=python3.7` where python3.7 was installed on the system with pyenv

## pipx vs pipsi
* pipx and pipsi both install packages in a similar way
* pipx is under active development. pipsi is no longer maintained.
* pipx always makes sure you're using the latest version of pip
* pipx has the ability to run a app in one line, leaving your system unchanged after it finishes (`pipx run APP`) where pipsi does not
* pipx has the ability to recursively install binaries from dependent packages
* pipx adds more useful information to its output
* pipx has more CLI options such as upgrade-all, reinstall-all, uninstall-all
* pipx is more modern. It uses Python 3.6+, and the `venv` package in the Python3 standard library instead of the python 2 package `virtualenv`.
* pipx works with Python homebrew installations while pipsi does not (at least on my machine)
* pipx defaults to less verbose output
* pipx allows you to see each command it runs by passing the --verbose flag
* pipx prints emojies 😀

Example interaction:
None. Either one or the other should be used. These tools compete for a similar workflow.

### Migrating to pipx from pipsi

After you have installed pipx, run [migrate_pipsi_to_pipx.py](https://raw.githubusercontent.com/pypa/pipx/master/scripts/migrate_pipsi_to_pipx.py). Why not do this with your new pipx installation?

```
pipx run https://raw.githubusercontent.com/pypa/pipx/master/scripts/migrate_pipsi_to_pipx.py
```

## pipx vs brew
* Both brew and pipx install cli tools
* They install them from different sources. brew uses a curated repository specifically for brew, and pipx generally uses PyPI.

Example interaction:
brew can be used to install pipx, but they generally don't interact much.

## pipx vs npx
* Both can run cli tools (npx will search for them in node_modules, and if not found run in a temporary environment. `pipx run` will search in `__pypackages__` and if not found run in a temporary environment)
* npx works with JavaScript and pipx works with Python
* Both tools attempt to make running executables written in a dynamic language (JS/Python) as easy as possible
* pipx can also install tools globally; npx cannot

Example interaction:
None. These tools work for different languages.

## pipx vs pip-run
[pip-run](https://github.com/jaraco/pip-run) is focused on running **arbitrary Python code in ephemeral environments** while pipx is focused on running **Python binaries in ephemeral and non-ephemeral environments**.

For example these two commands both install poetry to an ephemeral environment and invoke poetry with `--help`.
```
pipx run poetry --help
pip-run poetry -- -m poetry --help
```

Example interaction:
None.
