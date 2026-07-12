:orphan:

====
pipx
====

------------------------------------------------------------
install and run Python applications in isolated environments
------------------------------------------------------------

:Manual section: 1
:Manual group: User Commands

SYNOPSIS
--------

**pipx** [*global-options*] [**install** | **install-all** | **uninject** | **inject** | **pin** | **unpin** |
**upgrade** | **upgrade-all** | **upgrade-shared** | **uninstall** | **uninstall-all** | **reinstall** | **reinstall-
all** | **list** | **interpreter** | **run** | **runpip** | **ensurepath** | **environment** | **completions** |
**help**] [*command-options*]

DESCRIPTION
-----------

pipx installs and runs Python applications in isolated environments while exposing their commands on your
``PATH``.

COMMANDS
--------

**install**
    Install a package

**install-all**
    Install all packages

**uninject**
    Uninstall injected packages from an existing Virtual Environment

**inject**
    Install packages into an existing Virtual Environment

**pin**
    Pin the specified package to prevent it from being upgraded

**unpin**
    Unpin the specified package

**upgrade**
    Upgrade a package

**upgrade-all**
    Upgrade all packages. Runs ``pip install -U <pkgname>`` for each package.

**upgrade-shared**
    Upgrade shared libraries.

**uninstall**
    Uninstall a package

**uninstall-all**
    Uninstall all packages

**reinstall**
    Reinstall a package

**reinstall-all**
    Reinstall all packages

**list**
    List installed packages

**interpreter**
    Interact with interpreters managed by pipx

**run**
    Download the latest version of a package to a temporary virtual environment, then run an app from it. Also
    compatible with local ``__pypackages__`` directory (experimental).

**runpip**
    Run pip in an existing pipx-managed Virtual Environment

**ensurepath**
    Ensure directories necessary for pipx operation are in your PATH environment variable.

**environment**
    Print a list of environment variables and paths used by pipx.

**completions**
    Print instructions on enabling shell completions for pipx

**help**
    Show help for pipx or a command

Run **pipx** *command* **--help** for command-specific options.

GLOBAL OPTIONS
--------------

**-h**, **--help**
    show this help message and exit

**--version**
    Print version and exit

ENVIRONMENT VARIABLES
---------------------

**PIPX_HOME**
    Directory for pipx-managed environments and state.

**PIPX_BIN_DIR**
    Directory where pipx exposes application commands.

**PIPX_DEFAULT_PYTHON**
    Default interpreter used to create environments.

**PIPX_USE_EMOJI**
    Set to ``0`` to disable emoji output.

SEE ALSO
--------

Full documentation: https://pipx.pypa.io/

**pip**\(1), **virtualenv**\(1)

AUTHORS
-------

Chad Smith and contributors

https://github.com/pypa/pipx
