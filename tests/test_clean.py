"""Unit tests for the clean command."""

from helpers import (
    run_pipx_cli,
)
from pipx import paths


def test_clean_full(pipx_temp_env):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert paths.ctx.venvs.exists()
    assert paths.ctx.logs.exists()
    assert paths.ctx.venv_cache.exists()
    assert not run_pipx_cli(["clean", "--force"])
    assert not paths.ctx.venvs.exists()
    assert not paths.ctx.logs.exists()
    assert not paths.ctx.venv_cache.exists()


def test_clean_logs(pipx_temp_env):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert paths.ctx.venvs.exists()
    assert paths.ctx.logs.exists()
    assert paths.ctx.venv_cache.exists()
    assert not run_pipx_cli(["clean", "--logs", "--force"])
    assert paths.ctx.venvs.exists()
    assert not paths.ctx.logs.exists()
    assert paths.ctx.venv_cache.exists()


def test_clean_venvs(pipx_temp_env):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert paths.ctx.venvs.exists()
    assert paths.ctx.logs.exists()
    assert paths.ctx.venv_cache.exists()
    assert not run_pipx_cli(["clean", "--venvs", "--force"])
    assert not paths.ctx.venvs.exists()
    assert paths.ctx.logs.exists()
    assert paths.ctx.venv_cache.exists()


def test_clean_cache(pipx_temp_env):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert paths.ctx.venvs.exists()
    assert paths.ctx.logs.exists()
    assert paths.ctx.venv_cache.exists()
    assert not run_pipx_cli(["clean", "--cache", "--force"])
    assert paths.ctx.venvs.exists()
    assert paths.ctx.logs.exists()
    assert not paths.ctx.venv_cache.exists()


def test_clean_trash(pipx_temp_env):
    assert not run_pipx_cli(["install", "pycowsay"])
    trash_path = paths.ctx.trash
    trash_path.mkdir(parents=True, exist_ok=True)
    (trash_path / "temp_file").touch()
    assert paths.ctx.venvs.exists()
    assert paths.ctx.logs.exists()
    assert paths.ctx.venv_cache.exists()
    assert trash_path.exists()
    assert (trash_path / "temp_file").exists()
    assert not run_pipx_cli(["clean", "--trash", "--force"])
    assert paths.ctx.venvs.exists()
    assert paths.ctx.logs.exists()
    assert paths.ctx.venv_cache.exists()
    assert not trash_path.exists()


def test_all_clean_options(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert paths.ctx.venvs.exists()
    assert paths.ctx.logs.exists()
    assert paths.ctx.venv_cache.exists()
    assert not run_pipx_cli(["clean", "--venvs", "--logs", "--cache", "--trash", "--verbose", "--force"])
    captured = capsys.readouterr()
    assert "  Path: " in captured.out
    assert "Removing pycowsay..." in captured.out
    assert "Removing 1 installed package(s)..." in captured.out
    assert "All installed packages removed." in captured.out
