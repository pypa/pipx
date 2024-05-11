from helpers import run_pipx_cli, skip_if_windows


def test_runpip(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["runpip", "pycowsay", "list"])


@skip_if_windows
def test_runpip_global(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["install", "--global", "pycowsay"])
    assert not run_pipx_cli(["runpip", "--global", "pycowsay", "list"])
