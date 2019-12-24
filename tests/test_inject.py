#!/usr/bin/env python3
from helpers import run_pipx_cli


def test_simple(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "black"])


def test_spec(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "pylint==2.3.1"])


def test_include_apps(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert run_pipx_cli(["inject", "pycowsay", "black", "--include-deps"])
    assert not run_pipx_cli(
        ["inject", "pycowsay", "black", "--include-deps", "--include-apps"]
    )
