<p align="center">
<a href="https://pipx.pypa.io">
<img align="center" src="https://github.com/pypa/pipx/raw/main/logo.svg" width="200"/>
</a>
</p>

# pipx — Install and Run Python Applications in Isolated Environments

<p align="center">
<a href="https://github.com/pypa/pipx/raw/main/pipx_demo.gif">
<img src="https://github.com/pypa/pipx/raw/main/pipx_demo.gif"/>
</a>
</p>

<p align="center">
<a href="https://github.com/pypa/pipx/actions/workflows/tests.yml">
<img src="https://github.com/pypa/pipx/actions/workflows/tests.yml/badge.svg?event=push&branch=main" alt="image" /></a> <a href="https://badge.fury.io/py/pipx"><img src="https://badge.fury.io/py/pipx.svg" alt="PyPI version"></a> <a href="https://badge.fury.io/py/pipx"><img src="https://static.pepy.tech/badge/pipx"></a>

</p>

**Documentation**: <https://pipx.pypa.io>

**Source Code**: <https://github.com/pypa/pipx>

_For comparison to other tools including pipsi, see
[Comparison to Other Tools](https://pipx.pypa.io/stable/explanation/comparisons/)._

## Overview: What is `pipx`?

pipx is a tool to help you install and run end-user applications written in Python. It's roughly similar to macOS's
`brew`, JavaScript's [npx](https://medium.com/@maybekatz/introducing-npx-an-npm-package-runner-55f7d4bd282b), and
Linux's `apt`.

It's closely related to pip. In fact, it uses pip, but is focused on installing and managing Python packages that can be
run from the command line directly as applications.

### Features

`pipx` enables you to

- expose CLI entrypoints of packages ("apps") installed to isolated environments with the `install` command,
    guaranteeing no dependency conflicts and clean uninstalls;
- easily list, upgrade, and uninstall packages that were installed with pipx; and
- run the latest version of a Python application in a temporary environment with the `run` command.

Best of all, pipx runs with regular user permissions, never calling `sudo pip install`.

## Install pipx

### On macOS

```
brew install pipx
pipx ensurepath
```

### On Linux

```
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

### On Windows

```
scoop install pipx
pipx ensurepath
```

For more detailed installation instructions, see the
[full documentation](https://pipx.pypa.io/stable/how-to/install-pipx/).

## Quick Start

Install an application globally:

```
pipx install pycowsay
pycowsay mooo
```

Run an application without installing:

```
pipx run pycowsay moo
```

See the [full documentation](https://pipx.pypa.io/stable/) for more details.

## Contributing

Issues and Pull Requests are definitely welcome! Check out [Contributing](https://pipx.pypa.io/stable/contributing/) to
get started. Everyone who interacts with the pipx project via codebase, issue tracker, chat rooms, or otherwise is
expected to follow the [PSF Code of Conduct](https://github.com/pypa/.github/blob/main/CODE_OF_CONDUCT.md).
