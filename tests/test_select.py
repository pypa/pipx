from unittest import mock

from helpers import run_pipx_cli
from pipx import constants
from pipx.commands.common import find_selected_venvs_for_package
from pipx.venv import VenvContainer


def test_select(pipx_temp_env, capsys):
    """ Expose apps without suffix """
    assert not run_pipx_cli(["install", "shell-functools==0.2.0", "--suffix", "_2"])
    assert not run_pipx_cli(["install", "shell-functools==0.3.0", "--suffix", "_3"])
    assert not run_pipx_cli(["select", "shell-functools_3"])

    for app in ["filter", "foldl", "ft-functions", "map"]:
        app_path = constants.LOCAL_BIN_DIR / app
        assert app_path.exists()


def test_select_default(pipx_temp_env, capsys):
    """ Don't allow selecting non-suffixed venv """
    assert not run_pipx_cli(["install", "shell-functools"])
    assert run_pipx_cli(["select", "shell-functools"])
    assert "already has no suffix" in capsys.readouterr().err


def test_reselect(pipx_temp_env, capsys):
    """ Deselect old selected venv if other is selected """
    assert not run_pipx_cli(["install", "shell-functools==0.2.0", "--suffix", "_2"])
    assert not run_pipx_cli(["install", "shell-functools==0.3.0", "--suffix", "_3"])
    assert not run_pipx_cli(["select", "shell-functools_2"])
    assert not run_pipx_cli(["select", "shell-functools_3"])

    venv_container = VenvContainer(constants.PIPX_LOCAL_VENVS)
    selected_venvs = find_selected_venvs_for_package(venv_container, "shell-functools")
    assert len(selected_venvs) == 1


def test_select_no_shadow(pipx_temp_env, capsys):
    """ Don't allow select when it would shadow the package with no prefix """
    assert not run_pipx_cli(["install", "shell-functools==0.2.0", "--suffix", "_2"])
    assert not run_pipx_cli(["install", "shell-functools"])
    assert run_pipx_cli(["select", "shell-functools_2"])
    assert "already installed without suffix" in capsys.readouterr().err


def test_select_no_overwrite_with_install(pipx_temp_env, capsys):
    """ Don't allow install when it would overwrite existing binaries/symlinks pointing to a selected venv """
    assert not run_pipx_cli(["install", "shell-functools==0.2.0", "--suffix", "_2"])
    assert not run_pipx_cli(["select", "shell-functools_2"])
    assert run_pipx_cli(["install", "shell-functools"])


def test_select_upgrade(pipx_temp_env, capsys):
    """ Check if package stays selected and links still exist after upgrade """
    assert not run_pipx_cli(["install", "shell-functools==0.2.0", "--suffix", "_2"])
    assert not run_pipx_cli(["select", "shell-functools_2"])
    assert run_pipx_cli(["upgrade", "shell-functools_2"])

    # check still selected
    venv_container = VenvContainer(constants.PIPX_LOCAL_VENVS)
    selected_venvs = find_selected_venvs_for_package(venv_container, "shell-functools")
    assert len(selected_venvs) == 1
    assert selected_venvs[0].root.name == "shell-functools_2"

    # check links exist
    for app in ["filter", "foldl", "ft-functions", "map"]:
        app_path = constants.LOCAL_BIN_DIR / app
        assert app_path.exists()


def test_select_uninstall(pipx_temp_env, capsys):
    """ Check if links without suffix are gone after uninstall """
    assert not run_pipx_cli(["install", "shell-functools==0.2.0", "--suffix", "_2"])
    assert not run_pipx_cli(["select", "shell-functools_2"])
    assert not run_pipx_cli(["uninstall", "shell-functools_2"])

    for app in ["filter", "foldl", "ft-functions", "map"]:
        app_path = constants.LOCAL_BIN_DIR / app
        assert not app_path.exists()


# TODO: add deselect command
