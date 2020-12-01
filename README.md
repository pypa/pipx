<p align="center">
<a href="https://pipxproject.github.io/pipx/">
<img align="center" src="https://github.com/pipxproject/pipx/raw/master/logo.png"/>
</a>
</p>

# pipx — Install and Run Python Applications in Isolated Environments

<p align="center">
<a href="https://github.com/pipxproject/pipx/raw/master/pipx_demo.gif">
<img src="https://github.com/pipxproject/pipx/raw/master/pipx_demo.gif"/>
</a>
</p>

<p align="center">
<a href="https://github.com/pipxproject/pipx/actions?query=workflow%3ATest"><img src="https://github.com/pipxproject/pipx/workflows/Test/badge.svg?branch=master" alt="Test CI" ></a>
<a href="https://badge.fury.io/py/pipx"><img src="https://badge.fury.io/py/pipx.svg" alt="PyPI version"></a>
</p>

**Documentation**: https://pipxproject.github.io/pipx/

**Source Code**: https://github.com/pipxproject/pipx

_For comparison to other tools including pipsi, see [Comparison to Other Tools](https://pipxproject.github.io/pipx/comparisons/)._

## Install pipx

On macOS:

```
brew install pipx
pipx ensurepath
```

Upgrade pipx with `brew update && brew upgrade pipx`.

Otherwise, install via pip:

```
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

Upgrade pipx with `python3 -m pip install --user -U pipx`.

Shell completions are available by following the instructions printed with this command:
```
pipx completions
```

For more details, see the [installation instructions](https://pipxproject.github.io/pipx/installation/).


## Overview: What is `pipx`?

pipx is a tool to help you install and run end-user applications written in Python. It's roughly similar to macOS's `brew`, JavaScript's [npx](https://medium.com/@maybekatz/introducing-npx-an-npm-package-runner-55f7d4bd282b), and Linux's `apt`.

It's closely related to pip. In fact, it uses pip, but is focused on installing and managing Python packages that can be run from the command line directly as applications.

### How is it Different from pip?

pip is a general-purpose package installer for both libraries and apps with no environment isolation. pipx is made specifically for application installation, as it adds isolation yet still makes the apps available in your shell: pipx creates an isolated environment for each application and its associated packages.

pipx does not ship with pip, but installing it is often an important part of bootstrapping your system.


### Where Does `pipx` Install Apps From?
By default, pipx uses the same package index as pip, [PyPI](https://pypi.org/). pipx can also install from all other sources pip can, such as a local directory, wheel, git url, etc.

Python and PyPI allow developers to distribute code with "console script entry points". These entry points let users call into Python code from the command line, effectively acting like standalone applications.

pipx is a tool to install and run any of these thousands of application-containing packages in a safe, convenient, and reliable way. **In a way, it turns Python Package Index (PyPI) into a big app store for Python applications.** Not all Python packages have entry points, but many do.

If you would like to make your package compatible with pipx, all you need to do is add a [console scripts](https://python-packaging.readthedocs.io/en/latest/command-line-scripts.html#the-console-scripts-entry-point) entry point. If you're a poetry user, use [these instructions](https://python-poetry.org/docs/pyproject/#scripts).


## Features
`pipx` enables you to

- Expose CLI entrypoints of packages ("apps") installed to isolated environments with the `install` command. This guarantees no dependency conflicts and clean uninstalls!
- Easily list, upgrade, and uninstall packages that were installed with pipx
- Run the latest version of a Python application in a temporary environment with the `run` command

Best of all, pipx runs with regular user permissions, never calling `sudo pip install` (you aren't doing that, are you? 😄).


### Walkthrough: Installing a Package and its Applications With `pipx`

You can globally install an application by running

```
pipx install PACKAGE
```

This automatically creates a virtual environment, installs the package, and adds the package's associated applications (entry points) to a location on your `PATH`. For example, `pipx install pycowsay` makes the `pycowsay` command available globally, but sandboxes the pycowsay package in its own virtual environment. **pipx never needs to run as sudo to do this.**

Example:

```
>> pipx install pycowsay
  installed package pycowsay 2.0.3, Python 3.7.3
  These apps are now globally available
    - pycowsay
done! ✨ 🌟 ✨


>> pipx list
venvs are in /home/user/.local/pipx/venvs
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

### Walkthrough: Running an Application in a Temporary Virtual Environment

This is an alternative to `pipx install`.

`pipx run` downloads and runs the above mentioned Python "apps" in a one-time, temporary environment, leaving your system untouched afterwards.

This can be handy when you need to run the latest version of an app, but don't necessarily want it installed on your computer.

You may want to do this when you are initializing a new project and want to set up the right directory structure, when you want to view the help text of an application, or if you simply want to run an app in a one-off case and leave your system untouched afterwards.

For example, the blog post [How to set up a perfect Python project](https://sourcery.ai/blog/python-best-practices/) uses `pipx run` to kickstart a new project with [cookiecutter](https://github.com/cookiecutter/cookiecutter), a tool that creates projects from project templates.

A nice side benefit is that you don't have to remember to upgrade the app since `pipx run` will automatically run a recent version for you.

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

Re-running the same app is quick because pipx caches Virtual Environments on a per-app basis. The caches only last a few days, and when they expire, pipx will again use the latest version of the package. This way you can be sure you're always running a new version of the package without having to manually upgrade.

If the app name does not match that package name, you can use the `--spec` argument:
```
pipx run --spec PACKAGE APP
```

You can also use the `--spec` argument to run a specific version, or use any other `pip`-specifier:
```
pipx run --spec PACKAGE==1.0.0 APP
```

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
That's it! Those are the most important commands `pipx` offers. To see all of pipx's documentation, run `pipx --help` or see the [docs](https://pipxproject.github.io/pipx/docs/).

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

pipx was inspired by [pipsi](https://github.com/mitsuhiko/pipsi) and [npx](https://github.com/npm/npx). It was created by [Chad Smith](https://github.com/cs01/) and has had lots of help from [contributors](https://github.com/pipxproject/pipx/graphs/contributors). The logo was created by [@IrishMorales](https://github.com/IrishMorales).

pipx is maintained by a team of volunteers (in alphabetical order)

- [Bernát Gábor](https://github.com/gaborbernat)
- [Chad Smith](https://github.com/cs01) - co-lead maintainer
- [Matthew Clapp](https://github.com/itsayellow) - co-lead maintainer
- [Tzu-ping Chung](https://github.com/uranusjr)

## Contributing
Issues and Pull Requests are definitely welcome! Check out [Contributing](https://pipxproject.github.io/pipx/contributing/) to get started.
