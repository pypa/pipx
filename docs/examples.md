## `pipx install` examples
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

## `pipx run` examples

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

## `pipx inject` example

One use of the inject command is setting up a REPL with some useful extra packages.

```
pipx install ptpython
pipx inject ptpython requests pendulum
```

After running the above commands, you will be able to import and use the `requests` and `pendulum` packages inside a `ptpython` repl.


## `pipx list` example
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