from helpers import run_pipx_cli, skip_if_windows
from pipx import paths


def test_runpip(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["runpip", "pycowsay", "list"])


@skip_if_windows
def test_runpip_global(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["--global", "install", "pycowsay"])
    assert not run_pipx_cli(["--global", "runpip", "pycowsay", "list"])
    # reset to local to avoid side effects
    paths.ctx.make_local()
