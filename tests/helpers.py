from shutil import which
import subprocess
import sys
from typing import List
from unittest import mock

from pipx import main


def assert_not_in_virtualenv():
    assert not hasattr(sys, "real_prefix"), "Tests cannot run under virtualenv"
    # venv has been part of the stdlib since python3.3 https://www.python.org/dev/peps/pep-0405/
    assert getattr(sys, "base_prefix", sys.prefix) != sys.prefix or \
        sys.version_info >= (3,3), "Tests require venv"


def run_pipx_cli(pipx_args: List[str]):
    with mock.patch.object(sys, "argv", ["pipx"] + pipx_args):
        return main.cli()


def which_python(python_exe):
    try:
        pyenv_which = subprocess.run(
            ["pyenv", "which", python_exe],
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )
    except FileNotFoundError:
        # no pyenv on system
        return which(python_exe)

    if pyenv_which.returncode == 0:
        return pyenv_which.stdout.strip()
    else:
        # pyenv on system, but pyenv has no path to python_exe
        return None
