#!/usr/bin/env python3
from helpers import run_pipx_cli
from pipx import constants, util


def test_uninstall(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["uninstall", "pycowsay"])


def test_uninstall_with_missing_interpreter(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])

    _, python_path = util.get_venv_paths(constants.PIPX_LOCAL_VENVS / "pycowsay")
    assert (python_path).is_file()

    assert not run_pipx_cli(["uninstall", "pycowsay"])
