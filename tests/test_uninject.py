from helpers import run_pipx_cli
from package_info import PKG


def test_uninject_simple(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    assert not run_pipx_cli(["uninject", "pycowsay", "black"])


def test_uninject_with_include_apps(pipx_temp_env, capsys, caplog):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(
        ["inject", "pycowsay", PKG["black"]["spec"], "--include-deps", "--include-apps"]
    )
    assert not run_pipx_cli(["uninject", "pycowsay", "black", "--verbose"])
    assert "removed file" in caplog.text


def test_uninject_leave_deps(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    assert not run_pipx_cli(
        ["uninject", "pycowsay", "black", "--leave-deps", "--verbose"]
    )
    captured = capsys.readouterr()
    assert "Uninjected package black from venv pycowsay" in captured.out
    assert "Dependencies of uninstalled package:" not in captured.out
