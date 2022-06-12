import logging
import os
import subprocess
import sys
from unittest import mock

import pytest  # type: ignore

import pipx.main
import pipx.util
from helpers import run_pipx_cli
from package_info import PKG
from pipx import constants


def test_help_text(pipx_temp_env, monkeypatch, capsys):
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(
        ValueError, match="raised in test to exit early"
    ):
        run_pipx_cli(["run", "--help"])
    captured = capsys.readouterr()
    assert "Download the latest version of a package" in captured.out


def execvpe_mock(cmd_path, cmd_args, env):
    return_code = subprocess.run(
        [str(x) for x in cmd_args],
        env=env,
        stdout=None,
        stderr=None,
        encoding="utf-8",
        universal_newlines=True,
    ).returncode
    sys.exit(return_code)


def run_pipx_cli_exit(pipx_cmd_list, assert_exit=None):
    with pytest.raises(SystemExit) as sys_exit:
        run_pipx_cli(pipx_cmd_list)
    if assert_exit is not None:
        assert sys_exit.type == SystemExit
        assert sys_exit.value.code == assert_exit


@pytest.mark.parametrize(
    "package_name", ["pycowsay", "pycowsay==0.0.0.1", "pycowsay>=0.0.0.1"]
)
@mock.patch("os.execvpe", new=execvpe_mock)
def test_simple_run(pipx_temp_env, monkeypatch, capsys, package_name):
    run_pipx_cli_exit(["run", package_name, "--help"])
    captured = capsys.readouterr()
    assert "Download the latest version of a package" not in captured.out


@mock.patch("os.execvpe", new=execvpe_mock)
def test_cache(pipx_temp_env, monkeypatch, capsys, caplog):
    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])
    caplog.set_level(logging.DEBUG)
    run_pipx_cli_exit(["run", "--verbose", "pycowsay", "cowsay", "args"], assert_exit=0)
    assert "Reusing cached venv" in caplog.text

    run_pipx_cli_exit(["run", "--no-cache", "pycowsay", "cowsay", "args"])
    assert "Removing cached venv" in caplog.text


@mock.patch("os.execvpe", new=execvpe_mock)
def test_cachedir_tag(pipx_ultra_temp_env, monkeypatch, capsys, caplog):
    tag_path = constants.PIPX_VENV_CACHEDIR / "CACHEDIR.TAG"
    assert not tag_path.exists()

    # Run pipx to create tag
    caplog.set_level(logging.DEBUG)
    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])
    assert "Adding CACHEDIR.TAG to cache directory" in caplog.text
    assert tag_path.exists()
    caplog.clear()

    # Run pipx again to verify the tag file is not recreated
    run_pipx_cli_exit(["run", "pycowsay", "cowsay", "args"])
    assert "Adding CACHEDIR.TAG to cache directory" not in caplog.text
    assert tag_path.exists()

    # Verify the tag file starts with the required signature.
    with tag_path.open("r") as tag_file:
        assert tag_file.read().startswith("Signature: 8a477f597d28d172789f06886806bc55")


@mock.patch("os.execvpe", new=execvpe_mock)
def test_run_script_from_internet(pipx_temp_env, capsys):
    run_pipx_cli_exit(
        [
            "run",
            "https://gist.githubusercontent.com/cs01/"
            "fa721a17a326e551ede048c5088f9e0f/raw/"
            "6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py",
        ],
        assert_exit=0,
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
    "package, package_or_url, app_appargs, skip_win",
    [
        ("pycowsay", "pycowsay", ["pycowsay", "hello"], False),
        ("shell-functools", PKG["shell-functools"]["spec"], ["filter", "--help"], True),
        ("black", PKG["black"]["spec"], ["black", "--help"], False),
        ("pylint", PKG["pylint"]["spec"], ["pylint", "--help"], False),
        ("kaggle", PKG["kaggle"]["spec"], ["kaggle", "--help"], False),
        ("ipython", PKG["ipython"]["spec"], ["ipython", "--version"], False),
        ("cloudtoken", PKG["cloudtoken"]["spec"], ["cloudtoken", "--help"], True),
        ("awscli", PKG["awscli"]["spec"], ["aws", "--help"], True),
        # ("ansible", PKG["ansible"]["spec"], ["ansible", "--help"]), # takes too long
    ],
)
@mock.patch("os.execvpe", new=execvpe_mock)
def test_package_determination(
    caplog, pipx_temp_env, package, package_or_url, app_appargs, skip_win
):
    if sys.platform.startswith("win") and skip_win:
        # Skip packages with 'scripts' in setup.py that don't work on Windows
        pytest.skip()

    caplog.set_level(logging.INFO)

    run_pipx_cli_exit(
        ["run", "--verbose", "--spec", package_or_url, "--"] + app_appargs
    )

    assert "Cannot determine package name" not in caplog.text
    assert f"Determined package name: {package}" in caplog.text
