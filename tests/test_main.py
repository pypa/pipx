import argparse
import sys
from unittest import mock

import pytest

from helpers import run_pipx_cli
from pipx import constants, main


def test_help_text(monkeypatch, capsys):
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(ValueError, match="raised in test to exit early"):
        assert not run_pipx_cli(["--help"])
    captured = capsys.readouterr()
    assert "usage: pipx" in captured.out


def test_help_command_text(monkeypatch, capsys):
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(ValueError, match="raised in test to exit early"):
        assert not run_pipx_cli(["help"])
    captured = capsys.readouterr()
    mock_exit.assert_called_with(0)
    assert "usage: pipx" in captured.out


def test_help_command_for_subcommand(monkeypatch, capsys):
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(ValueError, match="raised in test to exit early"):
        assert not run_pipx_cli(["help", "install"])
    captured = capsys.readouterr()
    mock_exit.assert_called_with(0)
    assert "usage: pipx install" in captured.out


def test_version(monkeypatch, capsys):
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(ValueError, match="raised in test to exit early"):
        assert not run_pipx_cli(["--version"])
    captured = capsys.readouterr()
    mock_exit.assert_called_with(0)
    assert main.__version__ in captured.out.strip()


@pytest.mark.parametrize(
    ("argv", "executable", "expected"),
    [
        ("/usr/bin/pipx", "", "pipx"),
        ("__main__.py", "/usr/bin/python", "/usr/bin/python -m pipx"),
    ],
)
def test_prog_name(monkeypatch, argv, executable, expected):
    monkeypatch.setattr("pipx.main.sys.argv", [argv])
    monkeypatch.setattr("pipx.main.sys.executable", executable)
    assert main.prog_name() == expected


def test_limit_verbosity():
    assert not run_pipx_cli(["list", "-qqq"])
    assert not run_pipx_cli(["list", "-vvvv"])


def test_all_subcommands_have_func_registered():
    parser, _ = main.get_command_parser()
    subparsers_action = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    for name, subparser in subparsers_action.choices.items():
        assert callable(subparser._defaults.get("func")), f"{name!r} missing callable func default"
        for nested in (a for a in subparser._actions if isinstance(a, argparse._SubParsersAction)):
            for sub_name, sub_parser in nested.choices.items():
                assert callable(sub_parser._defaults.get("func")), f"{sub_name!r} missing callable func default"


def test_package_is_path_ignores_existing_directory(tmp_path, monkeypatch):
    # Regression for #1778: a directory in CWD with the same name as a
    # package should not be treated as a path.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "commit-check").mkdir()
    # Should not raise even though a directory of that name exists in CWD.
    main.package_is_path("commit-check")


@pytest.mark.parametrize(
    ("missing_raw", "python_raw", "expected_option", "expected_invalid"),
    [
        pytest.param(None, None, constants.FetchPythonOptions.NEVER, False, id="unset"),
        pytest.param("1", None, constants.FetchPythonOptions.MISSING, False, id="legacy-truthy"),
        pytest.param("0", None, constants.FetchPythonOptions.NEVER, False, id="legacy-falsy"),
        pytest.param(" False ", None, constants.FetchPythonOptions.NEVER, False, id="legacy-whitespace-falsy"),
        pytest.param("n", None, constants.FetchPythonOptions.NEVER, False, id="legacy-falsy-n"),
        pytest.param(None, "always", constants.FetchPythonOptions.ALWAYS, False, id="explicit-always"),
        pytest.param(None, "garbage", constants.FetchPythonOptions.NEVER, True, id="invalid-value"),
    ],
)
def test_compute_fetch_python(missing_raw, python_raw, expected_option, expected_invalid):
    option, invalid = constants._compute_fetch_python(missing_raw, python_raw)
    assert option is expected_option
    assert invalid is expected_invalid


@pytest.mark.parametrize(
    ("invalid", "fetch_python_raw", "missing_raw", "expected"),
    [
        pytest.param(True, "garbage", None, "PIPX_FETCH_PYTHON must be unset", id="invalid-value"),
        pytest.param(False, "missing", "1", "Setting both", id="both-env-vars"),
    ],
)
def test_validate_fetch_python_raises(monkeypatch, invalid, fetch_python_raw, missing_raw, expected):
    monkeypatch.setattr(main, "_FETCH_PYTHON_INVALID", invalid)
    monkeypatch.setattr(main, "_FETCH_PYTHON_RAW", fetch_python_raw)
    monkeypatch.setattr(main, "_FETCH_MISSING_PYTHON_RAW", missing_raw)
    with pytest.raises(main.PipxError, match=expected):
        main._validate_fetch_python()


def test_validate_fetch_python_deprecated_env_warning(monkeypatch, capsys):
    monkeypatch.setattr(main, "_FETCH_PYTHON_INVALID", False)
    monkeypatch.setattr(main, "_FETCH_PYTHON_RAW", None)
    monkeypatch.setattr(main, "_FETCH_MISSING_PYTHON_RAW", "1")
    main._validate_fetch_python()
    assert "PIPX_FETCH_MISSING_PYTHON is deprecated" in capsys.readouterr().err


def test_validate_fetch_python_passes_when_unset(monkeypatch):
    monkeypatch.setattr(main, "_FETCH_PYTHON_INVALID", False)
    monkeypatch.setattr(main, "_FETCH_PYTHON_RAW", None)
    monkeypatch.setattr(main, "_FETCH_MISSING_PYTHON_RAW", None)
    main._validate_fetch_python()


def test_deprecated_fetch_missing_python_silent_under_help(capsys):
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(ValueError, match="raised in test to exit early"):
        run_pipx_cli(["install", "--fetch-missing-python", "--help"])
    assert "--fetch-missing-python is deprecated" not in capsys.readouterr().err
