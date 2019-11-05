#!/usr/bin/env python3
from helpers import run_pipx_cli
from pipx import constants, util


def test_cli(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert "nothing has been installed with pipx" in captured.out


def test_missing_interpreter(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])

    _, python_path = util.get_venv_paths(constants.PIPX_LOCAL_VENVS / "pycowsay")
    assert (python_path).is_file()

    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert "package pycowsay has invalid interpreter" not in captured.out

    python_path.unlink()
    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert "package pycowsay has invalid interpreter" in captured.out
