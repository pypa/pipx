#!/usr/bin/env python3

import sys
from unittest import mock

import pytest  # type: ignore

from helpers import assert_not_in_virtualenv, run_pipx_cli
from pipx import main

assert_not_in_virtualenv()


@pytest.mark.parametrize(
    "ver_str,expected",
    [
        ["0.14.0.0", (0, 14)],
        ["0.14.0.0b0", (0, 14, 0, 0, "b", 0)],
        ["0.14", (0, 14)],
        ["0.14b0", (0, 14, 0, 0, "b", 0)],
        ["1.1.1.1", (1, 1, 1, 1)],
    ],
)
def test_simple_parse_version(ver_str, expected):
    assert main.simple_parse_version(ver_str) == expected


def test_help_text(monkeypatch, capsys):
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(
        ValueError, match="raised in test to exit early"
    ):
        assert not run_pipx_cli(["--help"])
    captured = capsys.readouterr()
    assert "usage: pipx" in captured.out


def test_version(monkeypatch, capsys):
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(
        ValueError, match="raised in test to exit early"
    ):
        assert not run_pipx_cli(["--version"])
    captured = capsys.readouterr()
    mock_exit.assert_called_with(0)
    assert main.__version__ in captured.out.strip()
