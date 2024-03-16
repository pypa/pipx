def test_pin(monkeypatch, capsys, pipx_temp_env):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["pin", "pycowsay"])
    assert not run_pipx_cli(["upgrade", "pycowsay"])
    captured = capsys.readouterr()
    assert "Not upgrading pinned package pycowsay" in captued.err