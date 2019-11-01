#!/usr/bin/env python3
import logging
import sys
from unittest import mock

import pytest  # type: ignore

from helpers import run_pipx_cli


def test_help_text(pipx_temp_env, monkeypatch, capsys):
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(
        ValueError, match="raised in test to exit early"
    ):
        run_pipx_cli(["run", "--help"])
    captured = capsys.readouterr()
    assert "Download the latest version of a package" in captured.out


def test_simple_run(pipx_temp_env, monkeypatch, capsys):
    run_pipx_cli(["run", "pycowsay", "--help"])
    captured = capsys.readouterr()
    assert "Download the latest version of a package" not in captured.out


def test_cache(pipx_temp_env, monkeypatch, capsys, caplog):
    caplog.set_level(logging.DEBUG)
    assert not run_pipx_cli(["run", "--verbose", "pycowsay", "cowsay", "args"])
    assert "Reusing cached venv" in caplog.text

    run_pipx_cli(["run", "--no-cache", "pycowsay", "cowsay", "args"])
    assert "Removing cached venv" in caplog.text


def test_run_script_from_internet(pipx_temp_env, capsys):
    assert not run_pipx_cli(
        [
            "run",
            "https://gist.githubusercontent.com/cs01/"
            "fa721a17a326e551ede048c5088f9e0f/raw/"
            "6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py",
        ]
    )


def test_appargs_doubledash(capsys):
    run_pipx_cli(["run", "pycowsay", "--", "hello"])
    captured = capsys.readouterr()
    assert "< -- hello >" not in captured.out
    run_pipx_cli(["run", "pycowsay", "hello", "--"])
    captured = capsys.readouterr()
    assert "< hello -- >" not in captured.out
    run_pipx_cli(["run", "pycowsay", "--"])
    captured = capsys.readouterr()
    assert "< -- >" not in captured.out
    run_pipx_cli(["run", "--", "pycowsay", "--", "hello"])
    captured = capsys.readouterr()
    assert "< -- hello >" not in captured.out
    run_pipx_cli(["run", "--", "pycowsay", "hello", "--"])
    captured = capsys.readouterr()
    assert "< hello -- >" not in captured.out
    run_pipx_cli(["run", "--", "pycowsay", "--"])
    captured = capsys.readouterr()
    assert "< -- >" not in captured.out
