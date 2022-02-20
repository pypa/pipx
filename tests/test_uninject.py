from helpers import run_pipx_cli
from package_info import PKG


def test_uninject_simple(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    assert not run_pipx_cli(["uninject", "pycowsay", PKG["black"]["spec"]])


def test_uninject_include_apps(pipx_temp_env, capsys):
    assert not run_pipx_cli(
        ["inject", "pycowsay", PKG["black"]["spec"], "--include-deps", "--include-apps"]
    )
    assert not run_pipx_cli(["uninject", "pycowsay", PKG["black"]["spec"]])
