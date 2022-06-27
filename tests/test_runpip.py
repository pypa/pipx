from helpers import run_pipx_cli


def test_runpip(pipx_temp_env, monkeypatch, capfd):
    with capfd.disabled():
        assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["runpip", "pycowsay", "freeze"])
    assert capfd.readouterr().out.startswith("pycowsay==")
