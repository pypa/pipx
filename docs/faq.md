## How does this compare to pipsi?
* pipx is under active development. pipsi is no longer maintained.
* pipx and pipsi both install packages in a similar way
* pipx always makes sure you're using the latest version of pip
* pipx has the ability to run a binary in one line, leaving your system unchanged after it finishes (`pipx run BINARY`) where pipsi does not
* pipx has the ability to recursively install binaries from dependent packages
* pipx adds more useful information to its output
* pipx has more CLI options such as upgrade-all, reinstall-all, uninstall-all
* pipx is more modern. It uses Python 3.6+, and the `venv` package in the Python3 standard library instead of the python 2 package `virtualenv`.
* pipx works with Python homebrew installations while pipsi does not (at least on my machine)
* pipx defaults to less verbose output
* pipx allows you to see each command it runs by passing the --verbose flag
* pipx prints emojies 😀

## Migrating to pipx from pipsi
Although `pipx` does not provide an automatic migration command,
it is pretty easy to do it from the command-line:

```bash
# install pipx with the recommended method
pip install --user pipx
userpath append ~/.local/bin
# you may have to open a new terminal here for pipx to be on your PATH

# migrate from pipsi to pipx
pipsi list | grep 'Package ' | cut -d\" -f2 | \
  while read -r p; do
    pipsi uninstall --yes "$p"
    # reinstall everything with python 3.6
    pipx install --python python3.6 "$p"
  done

# clean up
rm -rf ~/.local/pipsi
rm ~/.local/bin/pipsi
```

If you want to do this manually, you will have to remove pipsi's directory completely then reinstall everything with pipx.

First remove pipsi's directory (this is its default)
```
rm -r ~/.local/pipsi
```

There will still be files in `~/.local/bin` that point to `~/.local/pipsi/venvs`. If you reinstall the same packages with `pipx`, the files will be overwritten with valid files that point to the new pipx directory in `~/.local/pipx/venvs`. You may also want to remove files in `~/.local/bin`, but be sure the files you delete there were created by pipsi.

## How does this compare with `pip-run`?
[pip-run](https://github.com/jaraco/pip-run) is focused on running **arbitrary Python code in ephemeral environments** while pipx is focused on running **Python binaries in ephemeral and non-ephemeral environments**.

For example these two commands both install poetry to an ephemeral environment and invoke poetry with `--help`.
```
pipx run poetry --help
pip-run poetry -- -m poetry --help
```

