import pytest

from helpers import run_pipx_cli


def test_exec_nonexistent_package(pipx_temp_env, capsys):
    """Test that exec fails when the package is not installed."""
    assert run_pipx_cli(["exec", "nonexistent_package", "some_app"])
    captured = capsys.readouterr()
    assert "was not found" in captured.err


def test_exec_nonexistent_app(pipx_temp_env, capsys):
    """Test that exec fails when the app does not exist in the package."""
    assert not run_pipx_cli(["install", "pycowsay"])
    assert run_pipx_cli(["exec", "pycowsay", "nonexistent_app"])
    captured = capsys.readouterr()
    assert "not found" in captured.err


def test_exec_app_from_installed_package(pipx_temp_env, capsys):
    """Test that exec successfully runs an app from an installed package."""
    assert not run_pipx_cli(["install", "pycowsay"])
    with pytest.raises(SystemExit) as sys_exit:
        run_pipx_cli(["exec", "pycowsay", "pycowsay", "hello"])
    assert sys_exit.value.code == 0
