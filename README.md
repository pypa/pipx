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
<a href="https://github.com/pypa/pipx/actions">
<img src="https://github.com/pypa/pipx/workflows/tests/badge.svg?branch=main" alt="image" /></a> <a href="https://badge.fury.io/py/pipx"><img src="https://badge.fury.io/py/pipx.svg" alt="PyPI version"></a> <a href="https://badge.fury.io/py/pipx"><img src="https://static.pepy.tech/badge/pipx"></a>

</p>

**Documentation**: <https://pipx.pypa.io>

**Source Code**: <https://github.com/pypa/pipx>

_For comparison to other tools including pipsi, see
[Comparison to Other Tools](https://pipx.pypa.io/stable/comparisons/)._

## Install pipx

> [!WARNING]
>
> It is not recommended to install `pipx` via `pipx`. If you'd like to do this anyway, take a look at the
> [`pipx-in-pipx`](https://github.com/mattsb42-meta/pipx-in-pipx) project and read about the limitations there.

### On macOS

```
brew install pipx
pipx ensurepath
sudo pipx ensurepath --global # optional to allow pipx actions with --global argument
```

Upgrade pipx with `brew update && brew upgrade pipx`.

### On Linux

- Ubuntu 23.04 or above

```
sudo apt update
sudo apt install pipx
pipx ensurepath
sudo pipx ensurepath --global # optional to allow pipx actions with --global argument
```

- Fedora:

```
sudo dnf install pipx
pipx ensurepath
sudo pipx ensurepath --global # optional to allow pipx actions with --global argument
```

- Using `pip` on other distributions:

```
python3 -m pip install --user pipx
python3 -m pipx ensurepath
sudo pipx ensurepath --global # optional to allow pipx actions with --global argument
```

Upgrade pipx with `python3 -m pip install --user --upgrade pipx`.

### On Windows

- install via [Scoop](https://scoop.sh/)

```
scoop install pipx
pipx ensurepath
```

Upgrade pipx with `scoop update pipx`.

- install via pip (requires pip 19.0 or later)

```
# If you installed python using Microsoft Store, replace `py` with `python3` in the next line.
py -m pip install --user pipx
```

It is possible (even most likely) the above finishes with a WARNING looking similar to this:

```
WARNING: The script pipx.exe is installed in `<USER folder>\AppData\Roaming\Python\Python3x\Scripts` which is not on PATH
```

If so, go to the mentioned folder, allowing you to run the pipx executable directly. Enter the following line (even if
you did not get the warning):

```
.\pipx.exe ensurepath
```

This will add both the above mentioned path and the `%USERPROFILE%\.local\bin` folder to your search path. Restart your
terminal session and verify `pipx` does run.

Upgrade pipx with `py -m pip install --user --upgrade pipx`.

### Using pipx without installing (via zipapp)

You can also use pipx without installing it. The zipapp can be downloaded from
[Github releases](https://github.com/pypa/pipx/releases) and you can invoke it with a Python 3.7+ interpreter:

```
python pipx.pyz ensurepath
```

### Use with pre-commit

pipx [has pre-commit support](installation.md#pre-commit).

### Shell completions

Shell completions are available by following the instructions printed with this command:

```
pipx completions
```

For more details, see the [installation instructions](https://pipx.pypa.io/stable/installation/).

## Overview: What is `pipx`?

pipx is a tool to help you install and run end-user applications written in Python. It's roughly similar to macOS's
`brew`, JavaScript's [npx](https://medium.com/@maybekatz/introducing-npx-an-npm-package-runner-55f7d4bd282b), and
Linux's `apt`.

It's closely related to pip. In fact, it uses pip, but is focused on installing and managing Python packages that can be
run from the command line directly as applications.

### How is it Different from pip?

pip is a general-purpose package installer for both libraries and apps with no environment isolation. pipx is made
specifically for application installation, as it adds isolation yet still makes the apps available in your shell: pipx
creates an isolated environment for each application and its associated packages.

pipx does not ship with pip, but installing it is often an important part of bootstrapping your system.

### Where Does `pipx` Install Apps From?

By default, pipx uses the same package index as pip, [PyPI](https://pypi.org/). pipx can also install from all other
sources pip can, such as a local directory, wheel, git url, etc.

Python and PyPI allow developers to distribute code with "console script entry points". These entry points let users
call into Python code from the command line, effectively acting like standalone applications.

pipx is a tool to install and run any of these thousands of application-containing packages in a safe, convenient, and
reliable way. **In a way, it turns Python Package Index (PyPI) into a big app store for Python applications.** Not all
Python packages have entry points, but many do.

If you would like to make your package compatible with pipx, all you need to do is add a
[console scripts](https://python-packaging.readthedocs.io/en/latest/command-line-scripts.html#the-console-scripts-entry-point)
entry point. If you're a poetry user, use [these instructions](https://python-poetry.org/docs/pyproject/#scripts). Or,
if you're using hatch, [try this](https://hatch.pypa.io/latest/config/metadata/#cli).

## Features

`pipx` enables you to

- Expose CLI entrypoints of packages ("apps") installed to isolated environments with the `install` command. This
  guarantees no dependency conflicts and clean uninstalls!
- Easily list, upgrade, and uninstall packages that were installed with pipx
- Run the latest version of a Python application in a temporary environment with the `run` command

Best of all, pipx runs with regular user permissions, never calling `sudo pip install` (you aren't doing that, are you?
😄).

### Walkthrough: Installing a Package and its Applications With `pipx`

You can globally install an application by running

```
pipx install PACKAGE
```

This automatically creates a virtual environment, installs the package, and adds the package's associated applications
(entry points) to a location on your `PATH`. For example, `pipx install pycowsay` makes the `pycowsay` command available
globally, but sandboxes the pycowsay package in its own virtual environment. **pipx never needs to run as sudo to do
this.**

Example:

```
>> pipx install pycowsay
  installed package pycowsay 2.0.3, Python 3.7.3
  These apps are now globally available
    - pycowsay
done! ✨ 🌟 ✨


>> pipx list
venvs are in /home/user/.local/share/pipx/venvs
apps are exposed on your $PATH at /home/user/.local/bin
   package pycowsay 2.0.3, Python 3.7.3
    - pycowsay


# Now you can run pycowsay from anywhere
>> pycowsay mooo
  ____
< mooo >
  ====
         \
          \
            ^__^
            (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||

```

### Installing from Source Control

You can also install from a git repository. Here, `black` is used as an example.

```
pipx install git+https://github.com/psf/black.git
pipx install git+https://github.com/psf/black.git@branch  # branch of your choice
pipx install git+https://github.com/psf/black.git@ce14fa8b497bae2b50ec48b3bd7022573a59cdb1  # git hash
pipx install https://github.com/psf/black/archive/18.9b0.zip  # install a release
```

The pip syntax with `egg` must be used when installing extras:

```
pipx install "git+https://github.com/psf/black.git#egg=black[jupyter]"
```

### Inject a package

If an application installed by pipx requires additional packages, you can add them with pipx inject. For example, if you have ```ipython``` installed and want to add the ```matplotlib``` package to it, you would use:

```
pipx inject ipython matplotlib
```

### Walkthrough: Running an Application in a Temporary Virtual Environment

This is an alternative to `pipx install`.

`pipx run` downloads and runs the above mentioned Python "apps" in a one-time, temporary environment, leaving your
system untouched afterwards.

This can be handy when you need to run the latest version of an app, but don't necessarily want it installed on your
computer.

You may want to do this when you are initializing a new project and want to set up the right directory structure, when
you want to view the help text of an application, or if you simply want to run an app in a one-off case and leave your
system untouched afterwards.

For example, the blog post [How to set up a perfect Python project](https://sourcery.ai/blog/python-best-practices/)
uses `pipx run` to kickstart a new project with [cookiecutter](https://github.com/cookiecutter/cookiecutter), a tool
that creates projects from project templates.

A nice side benefit is that you don't have to remember to upgrade the app since `pipx run` will automatically run a
recent version for you.

Okay, let's see what this looks like in practice!

```
pipx run APP [ARGS...]
```

This will install the package in an isolated, temporary directory and invoke the app. Give it a try:

```
> pipx run pycowsay moo

  ---
< moo >
  ---
   \   ^__^
    \  (oo)\_______
       (__)\       )\/\
           ||----w |
           ||     ||


```

Notice that you **don't need to execute any install commands to run the app**.

Any arguments after the application name will be passed directly to the application:

```
> pipx run pycowsay these arguments are all passed to pycowsay!

  -------------------------------------------
< these arguments are all passed to pycowsay! >
  -------------------------------------------
   \   ^__^
    \  (oo)\_______
       (__)\       )\/\
           ||----w |
           ||     ||

```

### Ambiguous arguments

Sometimes pipx can consume arguments provided for the application:

```
> pipx run pycowsay --py

usage: pipx run [-h] [--no-cache] [--pypackages] [--spec SPEC] [--verbose] [--python PYTHON]
                [--system-site-packages] [--index-url INDEX_URL] [--editable] [--pip-args PIP_ARGS]
                app ...
pipx run: error: ambiguous option: --py could match --pypackages, --python
```

To prevent this put double dash `--` before APP. It will make pipx to forward the arguments to the right verbatim to the
application:

```
> pipx run -- pycowsay --py


  ----
< --py >
  ----
   \   ^__^
    \  (oo)\_______
       (__)\       )\/\
           ||----w |
           ||     ||


```

Re-running the same app is quick because pipx caches Virtual Environments on a per-app basis. The caches only last a few
days, and when they expire, pipx will again use the latest version of the package. This way you can be sure you're
always running a new version of the package without having to manually upgrade.

### Package with multiple apps, or the app name doesn't match the package name

If the app name does not match the package name, you can use the `--spec` argument to specify the `PACKAGE` name, and
provide the `APP` to run separately:

```
pipx run --spec PACKAGE APP
```

For example, the [esptool](https://github.com/espressif/esptool) package doesn't provide an executable with the same
name:

```
>> pipx run esptool
'esptool' executable script not found in package 'esptool'.
Available executable scripts:
    esp_rfc2217_server.py - usage: 'pipx run --spec esptool esp_rfc2217_server.py [arguments?]'
    espefuse.py - usage: 'pipx run --spec esptool espefuse.py [arguments?]'
    espsecure.py - usage: 'pipx run --spec esptool espsecure.py [arguments?]'
    esptool.py - usage: 'pipx run --spec esptool esptool.py [arguments?]'
```

You can instead run the executables that this package provides by using `--spec`:

```
pipx run --spec esptool esp_rfc2217_server.py
pipx run --spec esptool espefuse.py
pipx run --spec esptool espsecure.py
pipx run --spec esptool esptool.py
```

Note that the `.py` extension is not something you append to the executable name. It is part of the executable name, as
provided by the package. This can be anything. For example, when working with the
[pymodbus](https://github.com/pymodbus-dev/pymodbus) package:

```
>> pipx run pymodbus[repl]
'pymodbus' executable script not found in package 'pymodbus'.
Available executable scripts:
    pymodbus.console - usage: 'pipx run --spec pymodbus pymodbus.console [arguments?]'
    pymodbus.server - usage: 'pipx run --spec pymodbus pymodbus.server [arguments?]'
    pymodbus.simulator - usage: 'pipx run --spec pymodbus pymodbus.simulator [arguments?]'
```

You can run the executables like this:

```
pipx run --spec pymodbus[repl] pymodbus.console
pipx run --spec pymodbus[repl] pymodbus.server
pipx run --spec pymodbus[repl] pymodbus.simulator
```

### Running a specific version of a package

The `PACKAGE` argument above is actually a
[requirement specifier](https://packaging.python.org/en/latest/glossary/#term-Requirement-Specifier). Therefore, you can
also specify specific versions, version ranges, or extras. For example:

```
pipx run mpremote==1.20.0
pipx run --spec esptool==4.6.2 esptool.py
pipx run --spec 'esptool>=4.5' esptool.py
pipx run --spec 'esptool >= 4.5' esptool.py
```

Notice that some requirement specifiers have to be enclosed in quotes or escaped.

### Running from Source Control

You can also run from a git repository. Here, `black` is used as an example.

```
pipx run --spec git+https://github.com/psf/black.git black
pipx run --spec git+https://github.com/psf/black.git@branch black  # branch of your choice
pipx run --spec git+https://github.com/psf/black.git@ce14fa8b497bae2b50ec48b3bd7022573a59cdb1 black  # git hash
pipx run --spec https://github.com/psf/black/archive/18.9b0.zip black # install a release
```

### Running from URL

You can run .py files directly, too.

```
pipx run https://gist.githubusercontent.com/cs01/fa721a17a326e551ede048c5088f9e0f/raw/6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py
pipx is working!
```

### Summary

That's it! Those are the most important commands `pipx` offers. To see all of pipx's documentation, run `pipx --help` or
see the [docs](https://pipx.pypa.io/stable/docs/).

## Testimonials

<div>
"Thanks for improving the workflow that pipsi has covered in the past. Nicely done!"
<div style="text-align: right; margin-right: 10%; font-style:italic;">
—<a href="https://twitter.com/jezdez">Jannis Leidel</a>, PSF fellow, former pip and Django core developer, and founder of the Python Packaging Authority (PyPA)
</div>
</div>

<p></p>

<div>
"My setup pieces together pyenv, poetry, and pipx. [...] For the things I need, it’s perfect."
<div style="text-align: right; margin-right: 10%; font-style:italic;">
—<a href="https://twitter.com/jacobian">Jacob Kaplan-Moss</a>, co-creator of Django in blog post <a href="https://jacobian.org/2019/nov/11/python-environment-2020/">My Python Development Environment, 2020 Edition</a>
</div>
</div>

<p></p>

<div>
"I'm a big fan of pipx. I think pipx is super cool."
<div style="text-align: right; margin-right: 10%; font-style:italic;">
—<a href="https://twitter.com/mkennedy">Michael Kennedy</a>, co-host of PythonBytes podcast in <a href="https://pythonbytes.fm/episodes/transcript/139/f-yes-for-the-f-strings">episode 139</a>
</div>
</div>

<p></p>

## Credits

pipx was inspired by [pipsi](https://github.com/mitsuhiko/pipsi) and [npx](https://github.com/npm/npx). It was created
by [Chad Smith](https://github.com/cs01/) and has had lots of help from
[contributors](https://github.com/pypa/pipx/graphs/contributors). The logo was created by
[@IrishMorales](https://github.com/IrishMorales).

pipx is maintained by a team of volunteers (in alphabetical order)

- [Bernát Gábor](https://github.com/gaborbernat)
- [Chad Smith](https://github.com/cs01) - co-lead maintainer
- [Jason Lam](https://github.com/dukecat0)
- [Matthew Clapp](https://github.com/itsayellow) - co-lead maintainer
- [Tzu-ping Chung](https://github.com/uranusjr)

## Contributing

Issues and Pull Requests are definitely welcome! Check out [Contributing](https://pipx.pypa.io/stable/contributing/) to
get started. Everyone who interacts with the pipx project via codebase, issue tracker, chat rooms, or otherwise is
expected to follow the [PSF Code of Conduct](https://github.com/pypa/.github/blob/main/CODE_OF_CONDUCT.md).
