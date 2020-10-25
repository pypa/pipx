from unittest import mock

from helpers import run_pipx_cli
from pipx import constants
from pipx.commands.common import find_selected_venvs_for_package
from pipx.venv import VenvContainer


def test_deselect(pipx_temp_env, capsys):
    """ Remove links without suffix when deselecting """
    assert not run_pipx_cli(["install", "shell-functools==0.2.0", "--suffix", "_2"])
    assert not run_pipx_cli(["select", "shell-functools_2"])
    assert not run_pipx_cli(["deselect", "shell-functools_2"])

    for app in ["filter", "foldl", "ft-functions", "map"]:
        app_path_no_suffix = constants.LOCAL_BIN_DIR / app
        app_path_with_suffix = constants.LOCAL_BIN_DIR / f"{app}_2"
        assert not app_path_no_suffix.exists()
        assert app_path_with_suffix.exists()


def test_deselect_no_suffix(pipx_temp_env, capsys):
    """ Successfully deselect package when suffix is not passed """
    assert not run_pipx_cli(["install", "shell-functools==0.2.0", "--suffix", "_2"])
    assert not run_pipx_cli(["select", "shell-functools_2"])
    assert not run_pipx_cli(["deselect", "shell-functools"])
