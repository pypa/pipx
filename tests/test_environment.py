import fnmatch
from pathlib import Path

from helpers import run_pipx_cli, skip_if_windows
from pipx import paths
from pipx.commands.environment import ENVIRONMENT_VARIABLES
from pipx.paths import get_expanded_environ


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
    for env_var in ENVIRONMENT_VARIABLES:
        assert env_var in captured.out


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
    assert not run_pipx_cli(["environment", "--value", "PIPX_USE_EMOJI"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_HOME_ALLOW_SPACE"])

    assert run_pipx_cli(["environment", "--value", "SSS"])
    captured = capsys.readouterr()
    assert "Variable not found." in captured.err


def test_resolve_user_dir_in_env_paths(monkeypatch):
    monkeypatch.setenv("TEST_DIR", "~/test")
    home = Path.home()
    env_dir = get_expanded_environ("TEST_DIR")
    assert "~" not in str(env_dir)
    assert env_dir == home / "test"
    env_dir = get_expanded_environ("THIS_SHOULD_NOT_EXIST")
    assert env_dir is None


def test_allow_space_in_pipx_home(
    monkeypatch,
    capsys,
    tmp_path,
):
    home_dir = Path(tmp_path) / "path with space"
    monkeypatch.setattr(paths.ctx, "_base_home", home_dir)
    assert not run_pipx_cli(["environment", "--value", "PIPX_HOME_ALLOW_SPACE"])
    paths.ctx.log_warnings()
    captured = capsys.readouterr()
    assert "Found a space" in captured.err
    assert "false" in captured.out

    monkeypatch.setenv("PIPX_HOME_ALLOW_SPACE", "1")
    assert not run_pipx_cli(["environment", "--value", "PIPX_HOME_ALLOW_SPACE"])
    paths.ctx.log_warnings()
    captured = capsys.readouterr()
    assert "Found a space" not in captured.err
    assert "true" in captured.out

    paths.ctx.make_local()


@skip_if_windows
def test_cli_global(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["environment", "--global"])
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
    for env_var in ENVIRONMENT_VARIABLES:
        assert env_var in captured.out
