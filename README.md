# pipx: execute binaries from Python packages in isolated environments

<p align="center">
<a href="https://github.com/cs01/pipx/raw/master/pipx_demo.gif">
<img src="https://github.com/cs01/pipx/raw/master/pipx_demo.gif">
</a>

</p>

<a href="https://github.com/ambv/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>

*pipx is still a new project. Please submit issues if you have questions or bugs to report.*

pipx makes running the latest version of a program as easy as
```
> pipx BINARY
```

and (safely) installing a program globally as easy as
```
> pipx install PACKAGE
```

Read more on the [blog post](https://medium.com/@grassfedcode/bringing-some-of-javascripts-packaging-solutions-to-python-1b02430d589e).

Notice that you **don't need execute any install commands to run the binary**.

It eliminates the tedium of creating and removing virtualenvs, and removes the temptation to run `sudo pip install ...` (you aren't doing that, are you? 😄).

As a user, this makes trying out binaries really easy. As a developer, this means you can simplify your deployment instructions to users since they can try or install your program painlessly, and they are guaranteed to be running the latest version of your program.

pipx enables you to test various combinations of Python versions and package versions in ephemeral environments:
```
pipx BINARY  # latest version of binary is run with python3
pipx --spec PACKAGE==2.0.0 BINARY  # specific version of package is run
pipx --python 3.4 BINARY  # Installed and invoked with specific Python version
pipx --python 3.7 --spec PACKAGE=1.7.3 BINARY
pipx --spec git+https://url.git BINARY  # latest version on master is run
pipx --spec git+https://url.git@branch BINARY
pipx --spec git+https://url.git@hash BINARY
```

pipx lets you run Python programs with **no commitment** and no impact to your system, all while using best practices. For example, you can see help for any program by running `pipx BINARY --help`. When you use pipx to install a Python package, you get the best of both worlds: the package's binaries become avilable globally, but it runs in an isolated virtualenv -- and can be **cleanly** installed or updated.

pipx combines the features of JavaScript's [npx](https://medium.com/@maybekatz/introducing-npx-an-npm-package-runner-55f7d4bd282b) -- which ships with npm -- and Python's [pipsi](https://github.com/mitsuhiko/pipsi).

## usage
```
pipx binary
```

```
pipx [--spec PACKAGE] [--python PYTHON] binary [binary-arg] ...
```

```
pipx {install,upgrade,upgrade-all,uninstall,uninstall-all,list} [--help]
```

## install pipx
```
curl https://raw.githubusercontent.com/cs01/pipx/master/get-pipx.py | python3
```
python 3.6+ is required to install pipx. Binaries can be run with Python 3.3+.

To upgrade
```
pipx upgrade pipx
```

To uninstall
```
pipx uninstall pipx
```

## pipx commands

### run a binary
```
pipx BINARY
pipx [--python PYTHON] [--spec SPEC] BINARY [BINARYARGS]
```

There are a handful of other commands that can be run by pipx:
```
install, upgrade, upgrade-all, uninstall, uninstall-all, list
```
All of these are pretty self-explanatory. You can run `pipx COMMAND --help` for more.


### install
```
pipx install PACKAGE
```

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

### list installed packages/binaries
```
pipx list
```

## pipx run binary examples
```
pipx black
pipx --version black  # prints pipx version
pipx black  --version  # prints black version
pipx --python pythonX black
pipx --spec black==18.4a1 black --version
pipx --spec git+https://github.com/ambv/black.git black
pipx --spec git+https://github.com/ambv/black.git@branch-name black
pipx --spec git+https://github.com/ambv/black.git@git-hash black
pipx https://gist.githubusercontent.com/cs01/fa721a17a326e551ede048c5088f9e0f/raw/6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py
```

## install examples
```
pipx install gdbgui
pipx --python pythonX install gdbgui  # gdbgui will be associated with pythonX
pipx install gdbgui --spec git+https://github.com/cs01/gdbgui.git
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
The biggest difference is pipx has the ability to run a binary in one line:
```
pipx binary
```
where pipsi does not.

Both pipx and pipsi install packages to the system in a very similar way. pipx has taken inspiration from pipsi here. Still there are differences. Mainly, pipx aims to take advantage of the progress the Python ecosystem has made in the years since pipsi was created.

* implemenatation details
  * pipx requires Python 3.6+ and always uses the python3 module venv, rather than the Python 2 package virtualenv
  * pipx leverages existing Python APIs to find console entry points rather than locating and parsing files manually
* API differences
  * pipx does not require you to add "#egg=" to SVN urls when installing.
  * pipx has the --spec option to allow you to provide an SVN or a package version (package==2.0.0)
  * pipx allows you to upgrade all packages with one command
  * pipx allows you to uninstall all packages with one command
* pipx installs itself with python3
* pipx always uses the lastest version of pip in its venvs
* pipx defauls to less verbose output
* pipx allows you to see each command it runs by passing the --verbose flag
* pipx is under active development. The creator of pipsi has not been involved with the project for some time.
* pipx prints emojies 😀

## credits
pipx was inspired by [pipsi](https://github.com/mitsuhiko/pipsi) and [npx](https://github.com/zkat/npx).
