#!/usr/bin/env python3
import os
import logging
import sys
import subprocess
from unittest import mock

import pytest  # type: ignore

from helpers import run_pipx_cli

import pipx.main


def test_help_text(pipx_temp_env, monkeypatch, capsys):
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(
        ValueError, match="raised in test to exit early"
    ):
        run_pipx_cli(["run", "--help"])
    captured = capsys.readouterr()
    assert "Download the latest version of a package" in captured.out


def test_simple_run(pipx_temp_env, monkeypatch, capsys):
    run_pipx_cli(["run", "--", "pycowsay", "--help"])
    captured = capsys.readouterr()
    assert "Download the latest version of a package" not in captured.out


def test_cache(pipx_temp_env, monkeypatch, capsys, caplog):
    run_pipx_cli(["run", "--", "pycowsay", "cowsay", "args"])
    caplog.set_level(logging.DEBUG)
    assert not run_pipx_cli(["run", "--verbose", "--", "pycowsay", "cowsay", "args"])
    assert "Reusing cached venv" in caplog.text

    run_pipx_cli(["run", "--no-cache", "--", "pycowsay", "cowsay", "args"])
    assert "Removing cached venv" in caplog.text


def test_run_script_from_internet(pipx_temp_env, capsys):
    assert not run_pipx_cli(
        [
            "run",
            "--",
            "https://gist.githubusercontent.com/cs01/"
            "fa721a17a326e551ede048c5088f9e0f/raw/"
            "6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py",
        ]
    )


@pytest.mark.parametrize(
    "valid_args,input_run_args",
    [
        (False, ["pycowsay", "--", "hello"]),
        (False, ["pycowsay", "--", "--", "hello"]),
        (False, ["pycowsay", "hello", "--"]),
        (False, ["pycowsay", "hello", "--", "--"]),
        (False, ["pycowsay", "--"]),
        (False, ["pycowsay", "--", "--"]),
        (True, ["--", "pycowsay", "--", "hello"]),
        (True, ["--", "pycowsay", "--", "--", "hello"]),
        (True, ["--", "pycowsay", "hello", "--"]),
        (True, ["--", "pycowsay", "hello", "--", "--"]),
        (True, ["--", "pycowsay", "--"]),
        (True, ["--", "pycowsay", "--", "--"]),
    ],
)
def test_valid_args(pipx_temp_env, capsys, monkeypatch, input_run_args, valid_args):
    if valid_args:
        assert not run_pipx_cli(["run"] + input_run_args)
    else:
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            run_pipx_cli(["run"] + input_run_args)
        assert pytest_wrapped_e.value.code == 2
        captured = capsys.readouterr()
        assert (
            "pipx run: error: '--' is required before the app argument." in captured.err
        )


@pytest.mark.parametrize(
    "input_run_args,expected_appargs",
    [
        (["--", "pycowsay", "--", "hello"], ["--", "hello"]),
        (["--", "pycowsay", "--", "--", "hello"], ["--", "--", "hello"]),
        (["--", "pycowsay", "hello", "--"], ["hello", "--"]),
        (["--", "pycowsay", "hello", "--", "--"], ["hello", "--", "--"]),
        (["--", "pycowsay", "--"], ["--"]),
        (["--", "pycowsay", "--", "--"], ["--", "--"]),
    ],
)
def test_appargs_doubledash(
    pipx_temp_env, capsys, monkeypatch, input_run_args, expected_appargs
):
    parser = pipx.main.get_command_parser()
    monkeypatch.setattr(sys, "argv", ["pipx", "run"] + input_run_args)
    parsed_pipx_args = parser.parse_args()
    assert parsed_pipx_args.appargs == expected_appargs


def test_run_ensure_null_pythonpath():
    env = os.environ.copy()
    env["PYTHONPATH"] = "test"
    assert (
        "None"
        in subprocess.run(
            [
                sys.executable,
                "-m",
                "pipx",
                "run",
                "--",
                "ipython",
                "-c",
                "import os; print(os.environ.get('PYTHONPATH'))",
            ],
            universal_newlines=True,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
    )


# packages listed roughly in order of increasing test duration
@pytest.mark.parametrize(
    "package, package_or_url, app_appargs",
    [
        ("pycowsay", "pycowsay", ["pycowsay", "hello"]),
        ("shell-functools", "shell-functools", ["filter", "--help"]),
        ("black", "black", ["black", "--help"]),
        ("pylint", "pylint", ["pylint", "--help"]),
        ("kaggle", "kaggle", ["kaggle", "--help"]),
        ("ipython", "ipython", ["ipython", "--version"]),
        ("cloudtoken", "cloudtoken", ["cloudtoken", "--help"]),
        ("awscli", "awscli", ["aws", "--help"]),
        # ("ansible", "ansible", ["ansible", "--help"]), # takes too long
    ],
)
def test_package_determination(
    caplog, pipx_temp_env, package, package_or_url, app_appargs
):
    caplog.set_level(logging.INFO)

    run_pipx_cli(["run", "--verbose", "--spec", package_or_url, "--"] + app_appargs)

    assert "Cannot determine package name" not in caplog.text
    assert f"Determined package name: '{package}'" in caplog.text
