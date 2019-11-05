#!/usr/bin/env python3
import sys

from helpers import run_pipx_cli


def test_reinstall_all(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["reinstall-all", "--python", sys.executable])
