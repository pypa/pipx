#!/usr/bin/env python3
from helpers import run_pipx_cli
from pipx import constants


def test_uninstall(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["uninstall", "pycowsay"])


def test_uninstall_with_missing_interpreter(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])

    python_path = constants.PIPX_LOCAL_VENVS / "pycowsay" / "bin" / "python"
    assert (python_path).is_file()

    assert not run_pipx_cli(["uninstall", "pycowsay"])
