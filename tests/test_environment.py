from helpers import run_pipx_cli


def test_cli(monkeypatch, capsys):
    assert not run_pipx_cli(["environment"])
    captured = capsys.readouterr()
    assert "PIPX_HOME" in captured.out
    assert "PIPX_BIN_DIR" in captured.out
    assert "PIPX_SHARED_LIBS" in captured.out
    assert "PIPX_LOCAL_VENVS" in captured.out
    assert "PIPX_LOG_DIR" in captured.out
    assert "PIPX_TRASH_DIR" in captured.out
    assert "PIPX_VENV_CACHEDIR" in captured.out
    assert (
        "Only PIPX_HOME and PIPX_BIN_DIR can be set by users in the above list."
        in captured.out
    )


def test_cli_with_args(monkeypatch, capsys):
    assert not run_pipx_cli(["environment", "--value", "PIPX_HOME"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_BIN_DIR"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_SHARED_LIBS"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_LOCAL_VENVS"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_LOG_DIR"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_TRASH_DIR"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_VENV_CACHEDIR"])

    assert run_pipx_cli(["environment", "--value", "SSS"])
    captured = capsys.readouterr()
    assert "Variable not found." in captured.err
