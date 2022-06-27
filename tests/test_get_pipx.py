import os
import sys
from unittest import mock

from helpers import run_pipx_cli
from pipx import constants

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from get_pipx import main as get_pipx_main  # noqa: E402


def test_get_pipx(pipx_temp_env, capfd, monkeypatch, caplog):
    assert not run_pipx_cli(["list"])
    cap = capfd.readouterr()
    assert "nothing has been installed with pipx" in cap.err
    assert "These apps are now globally available" not in cap.out

    monkeypatch.setenv("PIPX_HOME", str(constants.PIPX_HOME))
    monkeypatch.setenv("BIN_DIR", str(constants.LOCAL_BIN_DIR))
    with mock.patch.object(
        sys,
        "argv",
        ["get_pipx"] + ["--verbose", "--no-modify-path", "--nowait", "--spec=."],
    ):
        get_pipx_main()
    cap = capfd.readouterr()
    assert "These apps are now globally available" in cap.out
    assert "- pipx" in cap.out
