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

After you have installed pipx, run this [gist](https://gist.githubusercontent.com/cs01/e72fc2e6a641a5105c4c22d83fe9cacc/raw/258582a6e7d8d4ac4b7313a48693264a5b6ea889/migrate_pipsi_to_pipx.py).
```
pipx run https://gist.githubusercontent.com/cs01/e72fc2e6a641a5105c4c22d83fe9cacc/raw/258582a6e7d8d4ac4b7313a48693264a5b6ea889/migrate_pipsi_to_pipx.py
```

## How does this compare with `pip-run`?
[pip-run](https://github.com/jaraco/pip-run) is focused on running **arbitrary Python code in ephemeral environments** while pipx is focused on running **Python binaries in ephemeral and non-ephemeral environments**.

For example these two commands both install poetry to an ephemeral environment and invoke poetry with `--help`.
```
pipx run poetry --help
pip-run poetry -- -m poetry --help
```

