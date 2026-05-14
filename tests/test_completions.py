from helpers import run_pipx_cli


def test_cli(monkeypatch, capsys):
    assert not run_pipx_cli(["completions"])
    captured = capsys.readouterr()
    assert "Add the appropriate command" in captured.out
