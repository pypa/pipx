import fnmatch
import os
from pathlib import Path

from helpers import run_pipx_cli, skip_if_windows


def load_dir_from_environ(dir_name: str, default: Path) -> Path:
    env = os.environ.get(dir_name, default)
    return Path(os.path.expanduser(env)).resolve()


def test_cli(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["environment"])
    captured = capsys.readouterr()
    assert fnmatch.fnmatch(captured.out, "*PIPX_HOME=*subdir/pipxhome*")
    assert fnmatch.fnmatch(captured.out, "*PIPX_BIN_DIR=*otherdir/pipxbindir*")
    assert fnmatch.fnmatch(captured.out, "*PIPX_MAN_DIR=*otherdir/pipxmandir*")
    assert "PIPX_SHARED_LIBS" in captured.out
    assert fnmatch.fnmatch(captured.out, "*PIPX_LOCAL_VENVS=*subdir/pipxhome/venvs*")
    assert fnmatch.fnmatch(captured.out, "*PIPX_LOG_DIR=*subdir/pipxhome/logs*")
    assert fnmatch.fnmatch(captured.out, "*PIPX_TRASH_DIR=*subdir/pipxhome/.trash*")
    assert fnmatch.fnmatch(captured.out, "*PIPX_VENV_CACHEDIR=*subdir/pipxhome/.cache*")
    # Checking just for the sake of completeness
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


@skip_if_windows
def test_cli_global(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["--global", "environment"])
    captured = capsys.readouterr()
    assert fnmatch.fnmatch(captured.out, "*PIPX_HOME=*global/pipxhome*")
    assert fnmatch.fnmatch(captured.out, "*PIPX_BIN_DIR=*global_otherdir/pipxbindir*")
    assert fnmatch.fnmatch(captured.out, "*PIPX_MAN_DIR=*global_otherdir/pipxmandir*")
    assert "PIPX_SHARED_LIBS" in captured.out
    assert fnmatch.fnmatch(captured.out, "*PIPX_LOCAL_VENVS=*global/pipxhome/venvs*")
    assert fnmatch.fnmatch(captured.out, "*PIPX_LOG_DIR=*global/pipxhome/logs*")
    assert fnmatch.fnmatch(captured.out, "*PIPX_TRASH_DIR=*global/pipxhome/.trash*")
    assert fnmatch.fnmatch(captured.out, "*PIPX_VENV_CACHEDIR=*global/pipxhome/.cache*")
    # Checking just for the sake of completeness
    assert "PIPX_DEFAULT_PYTHON" in captured.out
    assert "USE_EMOJI" in captured.out
