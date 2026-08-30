from __future__ import annotations

import fnmatch
import importlib
import re
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from helpers import run_pipx_cli, skip_if_windows
from pipx import paths
from pipx.commands.environment import DERIVED_ENVIRONMENT_VARIABLES, ENVIRONMENT_VARIABLES
from pipx.paths import get_expanded_environ

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

_ENVIRONMENT_VARIABLES_DOC: Final[Path] = Path(__file__).parents[1] / "docs" / "reference" / "environment-variables.rst"
# docstrfmt indents RST section titles by one space, and that indent is what keeps these off the prose naming
# the same sections further up the page.
_SETTABLE_HEADING: Final[str] = " Settable variables"
_DERIVED_HEADING: Final[str] = " Derived (read-only) values"
_DOC_TABLE_NAME: Final[re.Pattern[str]] = re.compile(
    r"""
    ^\ \ \ \ -\ -\ ``  # first cell of a list-table row, at the indent docstrfmt writes
    ([A-Z0-9_]+)       # the variable name, which the prose around the table spells the same way
    ``
    """,
    re.VERBOSE | re.MULTILINE,
)


@pytest.mark.usefixtures("pipx_temp_env")
def test_cli_value_skips_unrelated_discovery(
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # ``pipx.commands.__init__`` re-exports ``environment`` (the function), which shadows the submodule on the
    # package. ``import_module`` returns the module regardless.
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


@pytest.mark.parametrize(
    ("args", "home", "other"),
    [
        pytest.param([], "subdir/pipxhome", "otherdir", id="local"),
        pytest.param(["--global"], "global/pipxhome", "global_otherdir", id="global", marks=skip_if_windows),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_cli(capsys: pytest.CaptureFixture[str], args: list[str], home: str, other: str) -> None:
    assert not run_pipx_cli(["environment", *args])
    captured = capsys.readouterr()
    for pattern in (
        f"*PIPX_HOME=*{home}*",
        f"*PIPX_BIN_DIR=*{other}/pipxbindir*",
        f"*PIPX_MAN_DIR=*{other}/pipxmandir*",
        f"*PIPX_LOCAL_VENVS=*{home}/venvs*",
        f"*PIPX_LOG_DIR=*{home}/logs*",
        f"*PIPX_TRASH_DIR=*{home}/.trash*",
        f"*PIPX_VENV_CACHEDIR=*{home}/.cache*",
    ):
        assert fnmatch.fnmatch(captured.out, pattern)
    for env_var in ENVIRONMENT_VARIABLES:
        assert env_var in captured.out


@pytest.mark.parametrize(
    "variable",
    [
        "PIPX_HOME",
        "PIPX_BIN_DIR",
        "PIPX_MAN_DIR",
        "PIPX_SHARED_LIBS",
        "PIPX_LOCAL_VENVS",
        "PIPX_LOG_DIR",
        "PIPX_TRASH_DIR",
        "PIPX_VENV_CACHEDIR",
        "PIPX_DEFAULT_PYTHON",
        "PIPX_DISABLE_SHARED_LIBS_AUTO_UPGRADE",
        "PIPX_USE_EMOJI",
    ],
)
def test_cli_with_args(variable: str) -> None:
    assert not run_pipx_cli(["environment", "--value", variable])


def test_cli_rejects_unknown_value(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        run_pipx_cli(["environment", "--value", "SSS"])
    assert excinfo.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


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
        pytest.param(_SETTABLE_HEADING, _DERIVED_HEADING, ENVIRONMENT_VARIABLES, id="settable"),
        pytest.param(_DERIVED_HEADING, None, DERIVED_ENVIRONMENT_VARIABLES, id="derived"),
    ],
)
def test_reported_variables_match_the_documentation(start: str, end: str | None, reported: list[str]) -> None:
    # The `for env_var in ENVIRONMENT_VARIABLES` loop in `test_cli` reads the same list `environment()` prints from,
    # so a name missing from that list is invisible to it. The documentation table is the user-facing contract, so it
    # is the oracle here.
    documented = _documented_variables(start, end)
    assert documented, f"no variables parsed out of the {start.strip()!r} table"
    assert sorted(documented) == sorted(reported)


def _documented_variables(start: str, end: str | None) -> list[str]:
    text = _ENVIRONMENT_VARIABLES_DOC.read_text(encoding="utf-8")
    section = text[text.index(start) :]
    if end is not None:
        section = section[: section.index(end)]
    return _DOC_TABLE_NAME.findall(section)


def test_resolve_user_dir_in_env_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_DIR", "~/test")

    assert get_expanded_environ("TEST_DIR") == Path.home() / "test"


def test_resolve_missing_env_path() -> None:
    assert get_expanded_environ("THIS_SHOULD_NOT_EXIST") is None


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
