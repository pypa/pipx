import sys

import pytest  # type: ignore

from helpers import run_pipx_cli
from package_info import PKG


def test_uninject_simple(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    assert not run_pipx_cli(["uninject", "pycowsay", "black"])
    captured = capsys.readouterr()
    assert "Uninjected package black" in captured.out
    assert not run_pipx_cli(["list", "--include-injected"])
    captured = capsys.readouterr()
    assert "black" not in captured.out


def test_uninject_simple_global(pipx_temp_env, capsys):
    if sys.platform.startswith("win"):
        pytest.skip("This behavior is undefined on Windows")
    assert not run_pipx_cli(["--global", "install", "pycowsay"])
    assert not run_pipx_cli(["--global", "inject", "pycowsay", PKG["black"]["spec"]])
    assert not run_pipx_cli(["--global", "uninject", "pycowsay", "black"])
    captured = capsys.readouterr()
    assert "Uninjected package black" in captured.out
    assert not run_pipx_cli(["--global", "list", "--include-injected"])
    captured = capsys.readouterr()
    assert "black" not in captured.out


def test_uninject_with_include_apps(pipx_temp_env, capsys, caplog):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"], "--include-deps", "--include-apps"])
    assert not run_pipx_cli(["uninject", "pycowsay", "black", "--verbose"])
    assert "removed file" in caplog.text


def test_uninject_leave_deps(pipx_temp_env, capsys, caplog):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    assert not run_pipx_cli(["uninject", "pycowsay", "black", "--leave-deps", "--verbose"])
    captured = capsys.readouterr()
    assert "Uninjected package black from venv pycowsay" in captured.out
    assert "Dependencies of uninstalled package:" not in caplog.text
