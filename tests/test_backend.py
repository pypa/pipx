import os

from helpers import run_pipx_cli
from package_info import _exe_if_win


def test_custom_backend_venv(pipx_temp_env, capsys, caplog):
    assert not run_pipx_cli(["install", "--backend", "venv", "black"])
    captured = capsys.readouterr()
    assert "-m venv --without-pip" in caplog.text
    assert "installed package" in captured.out


def test_custom_backend_virtualenv(pipx_temp_env, capsys, caplog):
    assert not run_pipx_cli(["install", "--backend", "virtualenv", "nox"])
    captured = capsys.readouterr()
    assert f"{_exe_if_win("virtualenv")} --python" in caplog.text
    assert "installed package" in captured.out


def test_custom_backend_uv(pipx_temp_env, capsys, caplog):
    assert not run_pipx_cli(["install", "--backend", "uv", "pylint"])
    captured = capsys.readouterr()
    assert f"{_exe_if_win("uv")} venv" in caplog.text
    assert "installed package" in captured.out


def test_custom_installer_pip(pipx_temp_env, capsys, caplog):
    assert not run_pipx_cli(["install", "--installer", "pip", "pycowsay"])
    captured = capsys.readouterr()
    assert "pip --no-input" in caplog.text
    assert "installed package" in captured.out


def test_custom_installer_uv(pipx_temp_env, capsys, caplog):
    assert not run_pipx_cli(["install", "--installer", "uv", "sphinx"])
    captured = capsys.readouterr()
    assert f"{_exe_if_win("uv")} pip install" in caplog.text
    assert "installed package" in captured.out


def test_custom_installer_backend_uv(pipx_temp_env, capsys, caplog):
    assert not run_pipx_cli(["install", "--installer", "uv", "--backend", "uv", "black"])
    captured = capsys.readouterr()
    assert f"{_exe_if_win("uv")} venv" in caplog.text
    assert f"{_exe_if_win("uv")} pip install" in caplog.text
    assert "installed package" in captured.out


def test_custom_installer_uv_backend_venv(pipx_temp_env, capsys, caplog):
    assert not run_pipx_cli(["install", "--installer", "uv", "--backend", "venv", "nox"])
    captured = capsys.readouterr()
    assert "-m venv --without-pip" in caplog.text
    assert f"{_exe_if_win("uv")} pip install" in caplog.text
    assert "installed package" in captured.out


def test_custom_installer_uv_backend_virtualenv(pipx_temp_env, capsys, caplog):
    assert not run_pipx_cli(["install", "--installer", "uv", "--backend", "virtualenv", "pylint"])
    captured = capsys.readouterr()
    assert f"{_exe_if_win("virtualenv")} --python" in caplog.text
    assert f"{_exe_if_win("uv")} pip install" in caplog.text
    assert "installed package" in captured.out


def test_custom_installer_pip_backend_uv(pipx_temp_env, capsys, caplog):
    assert not run_pipx_cli(["install", "--installer", "pip", "--backend", "uv", "nox"])
    captured = capsys.readouterr()
    assert f"{_exe_if_win("uv")} venv" in caplog.text
    assert "-m pip" in caplog.text
    assert "installed package" in captured.out


def test_fallback_to_default(monkeypatch, pipx_temp_env, capsys, caplog):
    monkeypatch.setenv("PATH", os.getenv("PATH_TEST"))
    assert not run_pipx_cli(["install", "black", "--backend", "virtualenv", "--installer", "uv"])
    captured = capsys.readouterr()
    assert "'uv' not found on PATH" in caplog.text
    assert "'virtualenv' not found on PATH" in caplog.text
    assert "-m venv" in caplog.text
    assert "-m pip" in caplog.text
    assert "installed package" in captured.out
