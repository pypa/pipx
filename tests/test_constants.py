from pipx.constants import use_emjois
from pipx import constants
from unittest import mock
import sys
import pytest  # type: ignore

from helpers import run_pipx_cli


@pytest.mark.parametrize(
    "windows, USE_EMOJI, encoding, expected",
    [
        # windows
        (True, None, "utf-8", False),
        (True, "", "utf-8", False),
        (True, "0", "utf-8", False),
        (True, "1", "utf-8", True),
        (True, "true", "utf-8", True),
        (True, "tru", "utf-8", False),
        (True, "True", "utf-8", True),
        (True, "false", "utf-8", False),
        # unix
        (False, None, "utf-8", True),
        (False, "", "utf-8", False),
        (False, "0", "utf-8", False),
        (False, "1", "utf-8", True),
        (False, "true", "utf-8", True),
        (False, "tru", "utf-8", False),
        (False, "True", "utf-8", True),
        (False, "false", "utf-8", False),
        # encoding
        (False, None, "utf-8", True),
        (False, None, "", False),
    ],
)
def test_use_emjois(monkeypatch, windows, USE_EMOJI, encoding, expected):
    with mock.patch.object(
        constants,
        "is_windows",
        mock.create_autospec(constants.is_windows, return_value=windows),
    ), mock.patch.object(sys, "getdefaultencoding", return_value=encoding):
        if USE_EMOJI is not None:
            monkeypatch.setenv("USE_EMOJI", USE_EMOJI)
        assert use_emjois() is expected


def test_default_python(monkeypatch, capsys):
    monkeypatch.setattr(constants, "DEFAULT_PYTHON", "bad_python")
    run_pipx_cli(["install", "pycowsay"])
    captured = capsys.readouterr()
    assert "Default python interpreter 'bad_python' is invalid" in captured.err
