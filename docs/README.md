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

_For comparison to other tools including [pipsi](https://github.com/mitsuhiko/pipsi), see
[Comparison to Other Tools](https://pipx.pypa.io/stable/explanation/comparisons.html)._

## Overview: What is `pipx`?

pipx installs and runs end-user applications written in Python. It's roughly similar to macOS's [brew](https://brew.sh),
JavaScript's [npx](https://medium.com/@maybekatz/introducing-npx-an-npm-package-runner-55f7d4bd282b), and Linux's
[apt](https://wiki.debian.org/Apt).

It's closely related to [pip](https://pip.pypa.io). It installs with [uv](https://docs.astral.sh/uv/) when available and
`pip` otherwise, but focuses on installing and managing Python packages you run directly from the command line as
applications.

### Features

`pipx` enables you to

- expose CLI entrypoints of packages ("apps") installed to isolated environments with the `install` command,
    guaranteeing no dependency conflicts and clean uninstalls;
- list, upgrade, and uninstall packages you installed with pipx; and
- run the latest version of a Python application in a temporary environment with the `run` command.

pipx runs with regular user permissions and never calls `sudo pip install`.

## Install pipx

### On macOS

```
brew install pipx
pipx ensurepath
```

### On Linux

Install pipx with your distribution's package manager. See the
[Linux installation instructions](https://pipx.pypa.io/stable/how-to/install-pipx.html) for commands and alternatives.

```
pipx ensurepath
```

### On Windows

```
scoop install pipx
pipx ensurepath
```

For more detailed installation instructions, see the
[full documentation](https://pipx.pypa.io/stable/how-to/install-pipx.html).

## Quick Start

Install an application for your user:

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

Issues and pull requests are welcome. Check out [Contributing](https://pipx.pypa.io/stable/contributing.html) to get
started. We expect everyone who interacts with the pipx project via codebase, issue tracker, chat rooms, or otherwise to
follow the [PSF Code of Conduct](https://github.com/pypa/.github/blob/main/CODE_OF_CONDUCT.md).
