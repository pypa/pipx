## `pipx install` examples
```
pipx install pycowsay
pipx install --python python3.6 pycowsay
pipx install --python python3.7 pycowsay
pipx install git+https://github.com/psf/black
pipx install git+https://github.com/psf/black.git@branch-name
pipx install git+https://github.com/psf/black.git@git-hash
pipx install https://github.com/psf/black/archive/18.9b0.zip
pipx install black[d]
pipx install --include-deps jupyter
```

## `pipx run` examples

pipx enables you to test various combinations of Python versions and package versions in ephemeral environments:
```
pipx run BINARY  # latest version of binary is run with python3
pipx run --spec PACKAGE==2.0.0 BINARY  # specific version of package is run
pipx run --python 3.4 BINARY  # Installed and invoked with specific Python version
pipx run --python 3.7 --spec PACKAGE=1.7.3 BINARY
pipx run --spec git+https://url.git BINARY  # latest version on master is run
pipx run --spec git+https://url.git@branch BINARY
pipx run --spec git+https://url.git@hash BINARY
pipx run pycowsay moo
pipx --version  # prints pipx version
pipx run pycowsay --version  # prints pycowsay version
pipx run --python pythonX pycowsay
pipx run --spec pycowsay==2.0 pycowsay --version
pipx run --spec git+https://github.com/psf/black.git black
pipx run --spec git+https://github.com/psf/black.git@branch-name black
pipx run --spec git+https://github.com/psf/black.git@git-hash black
pipx run --spec https://github.com/psf/black/archive/18.9b0.zip black --help
pipx run https://gist.githubusercontent.com/cs01/fa721a17a326e551ede048c5088f9e0f/raw/6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py
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
