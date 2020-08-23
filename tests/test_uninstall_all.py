from helpers import run_pipx_cli


def test_uninstall_all(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["uninstall-all"])
