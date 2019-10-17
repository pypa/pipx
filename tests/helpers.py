import sys
from typing import List
from unittest import mock

from pipx import main


def assert_not_in_virtualenv():
    assert not hasattr(sys, "real_prefix"), "Tests cannot run under virtualenv"
    assert getattr(sys, "base_prefix", sys.prefix) != sys.prefix, "Tests require venv"


def run_pipx_cli(pipx_args: List[str]):
    with mock.patch.object(sys, "argv", ["pipx"] + pipx_args):
        return main.cli()
