import logging
import os
import subprocess
import sys
from unittest import mock

import pytest  # type: ignore

import pipx.main
import pipx.util
from helpers import run_pipx_cli


def test_help_text(pipx_temp_env, monkeypatch, capsys):
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(
        ValueError, match="raised in test to exit early"
    ):
        run_pipx_cli(["run", "--help"])
    captured = capsys.readouterr()
    assert "Download the latest version of a package" in captured.out


def exec_app_mock(cmd, env=None):
    """Mock function for pipx.util.exec_app"""

    if env is None:
        env = dict(os.environ)

    # TODO: are all these env adjustments necessary for exec* ?

    # Remove PYTHONPATH because some platforms (macOS with Homebrew) add pipx
    #   directories to it, and can make it appear to venvs as though pipx
    #   dependencies are in the venv path (#233)
    # Remove __PYVENV_LAUNCHER__ because it can cause the wrong python binary
    #   to be used (#334)
    env_blocklist = ["PYTHONPATH", "__PYVENV_LAUNCHER__"]
    for env_to_remove in env_blocklist:
        env.pop(env_to_remove, None)
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    # Make sure that Python writes output in UTF-8
    env["PYTHONIOENCODING"] = "utf-8"
    # Make sure we install package to venv, not userbase dir
    env["PIP_USER"] = "0"

    # make sure we show cursor again before handing over control
    # show_cursor()

    return subprocess.run(
        [str(x) for x in cmd],
        env=env,
        stdout=None,
        stderr=None,
        encoding="utf-8",
        universal_newlines=True,
    )


def test_simple_run(pipx_temp_env, monkeypatch, capsys):
    with mock.patch("pipx.util.exec_app", new=exec_app_mock):
        run_pipx_cli(["run", "pycowsay", "--help"])
    captured = capsys.readouterr()
    assert "Download the latest version of a package" not in captured.out


def test_cache(pipx_temp_env, monkeypatch, capsys, caplog):
    run_pipx_cli(["run", "pycowsay", "cowsay", "args"])
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


@pytest.mark.parametrize(
    "input_run_args,expected_app_with_args",
    [
        (["--", "pycowsay", "--", "hello"], ["pycowsay", "--", "hello"]),
        (["--", "pycowsay", "--", "--", "hello"], ["pycowsay", "--", "--", "hello"]),
        (["--", "pycowsay", "hello", "--"], ["pycowsay", "hello", "--"]),
        (["--", "pycowsay", "hello", "--", "--"], ["pycowsay", "hello", "--", "--"]),
        (["--", "pycowsay", "--"], ["pycowsay", "--"]),
        (["--", "pycowsay", "--", "--"], ["pycowsay", "--", "--"]),
        (["pycowsay", "--", "hello"], ["pycowsay", "--", "hello"]),
        (["pycowsay", "--", "--", "hello"], ["pycowsay", "--", "--", "hello"]),
        (["pycowsay", "hello", "--"], ["pycowsay", "hello", "--"]),
        (["pycowsay", "hello", "--", "--"], ["pycowsay", "hello", "--", "--"]),
        (["pycowsay", "--"], ["pycowsay", "--"]),
        (["pycowsay", "--", "--"], ["pycowsay", "--", "--"]),
        (["--", "--", "pycowsay", "--"], ["--", "pycowsay", "--"]),
    ],
)
def test_appargs_doubledash(
    pipx_temp_env, capsys, monkeypatch, input_run_args, expected_app_with_args
):
    parser = pipx.main.get_command_parser()
    monkeypatch.setattr(sys, "argv", ["pipx", "run"] + input_run_args)
    parsed_pipx_args = parser.parse_args()
    pipx.main.check_args(parsed_pipx_args)
    assert parsed_pipx_args.app_with_args == expected_app_with_args


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
    assert f"Determined package name: {package}" in caplog.text
