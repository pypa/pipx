import os
import sys
from pathlib import Path

import pytest  # type: ignore

from helpers import run_pipx_cli


def load_dir_from_environ(dir_name: str, default: Path) -> Path:
    env = os.environ.get(dir_name, default)
    return Path(os.path.expanduser(env)).resolve()


def test_cli(monkeypatch, capsys):
    assert not run_pipx_cli(["environment"])
    captured = capsys.readouterr()
    assert "PIPX_HOME" in captured.out
    assert "PIPX_BIN_DIR" in captured.out
    assert "PIPX_MAN_DIR" in captured.out
    assert "PIPX_SHARED_LIBS" in captured.out
    assert "PIPX_LOCAL_VENVS" in captured.out
    assert "PIPX_LOG_DIR" in captured.out
    assert "PIPX_TRASH_DIR" in captured.out
    assert "PIPX_VENV_CACHEDIR" in captured.out
    assert "PIPX_DEFAULT_PYTHON" in captured.out
    assert "USE_EMOJI" in captured.out
    assert "Environment variables (set by user):" in captured.out


def test_cli_with_args(monkeypatch, capsys):
    assert not run_pipx_cli(["environment", "--value", "PIPX_HOME"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_BIN_DIR"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_MAN_DIR"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_SHARED_LIBS"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_LOCAL_VENVS"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_LOG_DIR"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_TRASH_DIR"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_VENV_CACHEDIR"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_DEFAULT_PYTHON"])
    assert not run_pipx_cli(["environment", "--value", "USE_EMOJI"])

    assert run_pipx_cli(["environment", "--value", "SSS"])
    captured = capsys.readouterr()
    assert "Variable not found." in captured.err


def test_resolve_user_dir_in_env_paths(monkeypatch):
    monkeypatch.setenv("TEST_DIR", "~/test")
    home = Path.home()
    env_dir = load_dir_from_environ("TEST_DIR", Path.home())
    assert "~" not in str(env_dir)
    assert env_dir == home / "test"


def test_resolve_user_dir_in_env_paths_env_not_set(monkeypatch):
    home = Path.home()
    env_dir = load_dir_from_environ("TEST_DIR", Path.home())
    assert env_dir == home


def test_cli_global(monkeypatch, capsys):
    if sys.platform.startswith("win"):
        pytest.skip("This behavior is undefined on Windows")
    assert not run_pipx_cli(["--global", "environment"])
    captured = capsys.readouterr()
    assert "PIPX_HOME=/opt/pipx" in captured.out
    assert "PIPX_BIN_DIR=/usr/local/bin" in captured.out
    assert "PIPX_MAN_DIR=/usr/local/share/man" in captured.out
    assert "PIPX_SHARED_LIBS=/opt/pipx/shared" in captured.out
    assert "PIPX_LOCAL_VENVS=/opt/pipx/venvs" in captured.out
    assert "PIPX_LOG_DIR=/opt/pipx/logs" in captured.out
    assert "PIPX_TRASH_DIR=/opt/pipx/.trash" in captured.out
    assert "PIPX_VENV_CACHEDIR=/opt/pipx/.cache" in captured.out
    # Checking just for the sake of completeness
    assert "PIPX_DEFAULT_PYTHON" in captured.out
    assert "USE_EMOJI" in captured.out
