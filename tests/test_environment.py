from __future__ import annotations

import fnmatch
import importlib
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from helpers import run_pipx_cli, skip_if_windows
from pipx import paths
from pipx.commands.environment import DERIVED_ENVIRONMENT_VARIABLES, ENVIRONMENT_VARIABLES
from pipx.paths import get_expanded_environ

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

ENVIRONMENT_VARIABLES_DOC = Path(__file__).parents[1] / "docs" / "reference" / "environment-variables.rst"
SETTABLE_HEADING = " Settable variables"
DERIVED_HEADING = " Derived (read-only) values"
# First cell of a list-table row. Anchored so the surrounding prose, which also names variables, is not picked up.
DOC_TABLE_NAME = re.compile(r"^    - - ``([A-Z0-9_]+)``", re.MULTILINE)


def documented_variables(start: str, end: str | None = None) -> list[str]:
    text = ENVIRONMENT_VARIABLES_DOC.read_text(encoding="utf-8")
    section = text[text.index(start) :]
    if end is not None:
        section = section[: section.index(end)]
    return DOC_TABLE_NAME.findall(section)


@pytest.mark.usefixtures("pipx_temp_env")
def test_cli_value_skips_unrelated_discovery(
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    environment_module = importlib.import_module("pipx.commands.environment")
    resolve_backend_name = mocker.patch.object(
        environment_module,
        "resolve_backend_name",
        autospec=True,
        return_value=("pip", "auto-pip"),
    )
    find_uv_binary = mocker.patch.object(
        environment_module,
        "find_uv_binary",
        autospec=True,
        return_value=(None, "missing"),
    )
    get_default_python = mocker.patch.object(environment_module, "get_default_python", autospec=True)

    assert not run_pipx_cli(["environment", "--value", "PIPX_HOME"])

    assert capsys.readouterr().out.strip() == str(paths.ctx.home)
    resolve_backend_name.assert_not_called()
    find_uv_binary.assert_not_called()
    get_default_python.assert_not_called()


@pytest.mark.usefixtures("pipx_temp_env")
def test_cli(capsys: pytest.CaptureFixture[str]) -> None:
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


def test_cli_with_args(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["environment", "--value", "PIPX_HOME"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_BIN_DIR"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_MAN_DIR"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_SHARED_LIBS"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_LOCAL_VENVS"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_LOG_DIR"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_TRASH_DIR"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_VENV_CACHEDIR"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_DEFAULT_PYTHON"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_DISABLE_SHARED_LIBS_AUTO_UPGRADE"])
    assert not run_pipx_cli(["environment", "--value", "PIPX_USE_EMOJI"])

    with pytest.raises(SystemExit) as excinfo:
        run_pipx_cli(["environment", "--value", "SSS"])
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "invalid choice" in captured.err


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("PIPX_GLOBAL_HOME", "global-home"),
        ("PIPX_GLOBAL_BIN_DIR", "global-bin"),
        ("PIPX_GLOBAL_MAN_DIR", "global-man"),
        ("PIPX_DEFAULT_BACKEND", "pip"),
        ("PIPX_FETCH_MISSING_PYTHON", "1"),
        ("PIPX_FETCH_PYTHON", "missing"),
        ("PIPX_MAX_LOGS", "3"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_cli_with_user_environment_value(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    variable: str,
    value: str,
) -> None:
    monkeypatch.setenv(variable, value)

    assert not run_pipx_cli(["environment", "--value", variable])
    assert capsys.readouterr().out == f"{value}\n"


@pytest.mark.parametrize(
    ("start", "end", "reported"),
    [
        pytest.param(SETTABLE_HEADING, DERIVED_HEADING, ENVIRONMENT_VARIABLES, id="settable"),
        pytest.param(DERIVED_HEADING, None, DERIVED_ENVIRONMENT_VARIABLES, id="derived"),
    ],
)
def test_reported_variables_match_the_documentation(start: str, end: str | None, reported: list[str]) -> None:
    # The `for env_var in ENVIRONMENT_VARIABLES` loops in `test_cli` and `test_cli_global` read the same list
    # `environment()` prints from, so a name missing from that list is invisible to them. The documentation table is
    # the user-facing contract, so it is the oracle here.
    documented = documented_variables(start, end)
    assert documented, f"no variables parsed out of the {start.strip()!r} table"
    assert sorted(documented) == sorted(reported)


def test_resolve_user_dir_in_env_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_DIR", "~/test")
    home = Path.home()
    env_dir = get_expanded_environ("TEST_DIR")
    assert "~" not in str(env_dir)
    assert env_dir == home / "test"
    env_dir = get_expanded_environ("THIS_SHOULD_NOT_EXIST")
    assert env_dir is None


@pytest.mark.parametrize(
    "env_name",
    [
        "PIPX_HOME",
        "PIPX_GLOBAL_HOME",
        "PIPX_BIN_DIR",
        "PIPX_GLOBAL_BIN_DIR",
        "PIPX_MAN_DIR",
        "PIPX_GLOBAL_MAN_DIR",
        "PIPX_SHARED_LIBS",
    ],
)
def test_resolve_empty_env_paths(monkeypatch: pytest.MonkeyPatch, env_name: str) -> None:
    monkeypatch.setenv(env_name, "")

    assert get_expanded_environ(env_name) is None


def test_cli_logs_fallback_home(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fallback_home = tmp_path / "fallback"
    fallback_home.mkdir()
    monkeypatch.setattr(paths.ctx, "_base_home", tmp_path / "specific")
    monkeypatch.setattr(paths.ctx, "_fallback_home", fallback_home)

    assert not run_pipx_cli(["environment", "--verbose"])

    assert "Both a specific pipx home folder" in capsys.readouterr().err


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env")
def test_cli_global(capsys: pytest.CaptureFixture[str]) -> None:
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
