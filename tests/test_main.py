import sys
from unittest import mock

import pytest  # type: ignore

from helpers import run_pipx_cli
from pipx import main


def test_help_text(monkeypatch, capsys):
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(ValueError, match="raised in test to exit early"):
        assert not run_pipx_cli(["--help"])
    captured = capsys.readouterr()
    assert "usage: pipx" in captured.out


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
