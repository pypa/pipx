from __future__ import annotations

import fnmatch
import importlib
import re
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from helpers import SKIP_IF_WINDOWS, run_pipx_cli
from pipx import paths
from pipx.commands.environment import DERIVED_ENVIRONMENT_VARIABLES, ENVIRONMENT_VARIABLES
from pipx.paths import get_expanded_environ

if TYPE_CHECKING:
    from unittest.mock import MagicMock

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
    environment_module: Final = importlib.import_module("pipx.commands.environment")
    resolve_backend_name: Final[MagicMock] = mocker.patch.object(
        environment_module,
        "resolve_backend_name",
        autospec=True,
        return_value=("pip", "auto-pip"),
    )
    find_uv_binary: Final[MagicMock] = mocker.patch.object(
        environment_module,
        "find_uv_binary",
        autospec=True,
        return_value=(None, "missing"),
    )
    get_default_python: Final[MagicMock] = mocker.patch.object(environment_module, "get_default_python", autospec=True)

    assert not run_pipx_cli(["environment", "--value", "PIPX_HOME"])

    assert (
        capsys.readouterr().out.strip(),
        resolve_backend_name.call_count,
        find_uv_binary.call_count,
        get_default_python.call_count,
    ) == (str(paths.CTX.home), 0, 0, 0)


@pytest.mark.parametrize(
    ("args", "home", "other"),
    [
        pytest.param([], "subdir/pipxhome", "otherdir", id="local"),
        pytest.param(["--global"], "global/pipxhome", "global_otherdir", id="global", marks=SKIP_IF_WINDOWS),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_cli(capsys: pytest.CaptureFixture[str], args: list[str], home: str, other: str) -> None:
    assert not run_pipx_cli(["environment", *args])

    output: Final[str] = capsys.readouterr().out
    unmatched: Final[list[str]] = [
        pattern
        for pattern in (
            f"*PIPX_HOME=*{home}*",
            f"*PIPX_BIN_DIR=*{other}/pipxbindir*",
            f"*PIPX_MAN_DIR=*{other}/pipxmandir*",
            f"*PIPX_LOCAL_VENVS=*{home}/venvs*",
            f"*PIPX_LOG_DIR=*{home}/logs*",
            f"*PIPX_TRASH_DIR=*{home}/.trash*",
            f"*PIPX_VENV_CACHEDIR=*{home}/.cache*",
        )
        if not fnmatch.fnmatch(output, pattern)
    ]
    assert (unmatched, [variable for variable in ENVIRONMENT_VARIABLES if variable not in output]) == ([], [])


@pytest.mark.parametrize(
    "variable",
    [
        pytest.param("PIPX_HOME", id="PIPX_HOME"),
        pytest.param("PIPX_BIN_DIR", id="PIPX_BIN_DIR"),
        pytest.param("PIPX_MAN_DIR", id="PIPX_MAN_DIR"),
        pytest.param("PIPX_SHARED_LIBS", id="PIPX_SHARED_LIBS"),
        pytest.param("PIPX_LOCAL_VENVS", id="PIPX_LOCAL_VENVS"),
        pytest.param("PIPX_LOG_DIR", id="PIPX_LOG_DIR"),
        pytest.param("PIPX_TRASH_DIR", id="PIPX_TRASH_DIR"),
        pytest.param("PIPX_VENV_CACHEDIR", id="PIPX_VENV_CACHEDIR"),
        pytest.param("PIPX_DEFAULT_PYTHON", id="PIPX_DEFAULT_PYTHON"),
        pytest.param("PIPX_DISABLE_SHARED_LIBS_AUTO_UPGRADE", id="PIPX_DISABLE_SHARED_LIBS_AUTO_UPGRADE"),
        pytest.param("PIPX_USE_EMOJI", id="PIPX_USE_EMOJI"),
    ],
)
def test_cli_with_args(variable: str) -> None:
    assert not run_pipx_cli(["environment", "--value", variable])


def test_cli_rejects_unknown_value(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        run_pipx_cli(["environment", "--value", "SSS"])

    assert (excinfo.value.code, "invalid choice" in capsys.readouterr().err) == (2, True)


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        pytest.param("PIPX_GLOBAL_HOME", "global-home", id="PIPX_GLOBAL_HOME-global-home"),
        pytest.param("PIPX_GLOBAL_BIN_DIR", "global-bin", id="PIPX_GLOBAL_BIN_DIR-global-bin"),
        pytest.param("PIPX_GLOBAL_MAN_DIR", "global-man", id="PIPX_GLOBAL_MAN_DIR-global-man"),
        pytest.param("PIPX_DEFAULT_BACKEND", "pip", id="PIPX_DEFAULT_BACKEND-pip"),
        pytest.param("PIPX_FETCH_MISSING_PYTHON", "1", id="PIPX_FETCH_MISSING_PYTHON-1"),
        pytest.param("PIPX_FETCH_PYTHON", "missing", id="PIPX_FETCH_PYTHON-missing"),
        pytest.param("PIPX_MAX_LOGS", "3", id="PIPX_MAX_LOGS-3"),
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
    # test_cli checks the list environment() prints from, so it cannot see a name missing from that list; the
    # documentation table is the user-facing contract
    documented: Final[list[str]] = _documented_variables(start, end)
    assert documented, f"no variables parsed out of the {start.strip()!r} table"
    assert sorted(documented) == sorted(reported)


def _documented_variables(start: str, end: str | None) -> list[str]:
    text: Final[str] = _ENVIRONMENT_VARIABLES_DOC.read_text(encoding="utf-8")
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
        pytest.param("PIPX_HOME", id="PIPX_HOME"),
        pytest.param("PIPX_GLOBAL_HOME", id="PIPX_GLOBAL_HOME"),
        pytest.param("PIPX_BIN_DIR", id="PIPX_BIN_DIR"),
        pytest.param("PIPX_GLOBAL_BIN_DIR", id="PIPX_GLOBAL_BIN_DIR"),
        pytest.param("PIPX_MAN_DIR", id="PIPX_MAN_DIR"),
        pytest.param("PIPX_GLOBAL_MAN_DIR", id="PIPX_GLOBAL_MAN_DIR"),
        pytest.param("PIPX_SHARED_LIBS", id="PIPX_SHARED_LIBS"),
    ],
)
def test_resolve_empty_env_paths(monkeypatch: pytest.MonkeyPatch, env_name: str) -> None:
    monkeypatch.setenv(env_name, "")

    assert get_expanded_environ(env_name) is None


@pytest.mark.usefixtures("pipx_temp_env")
def test_cli_logs_fallback_home(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fallback_home: Final[Path] = tmp_path / "fallback"
    fallback_home.mkdir()
    monkeypatch.setattr(paths, "FALLBACK_PIPX_HOMES", [fallback_home])
    paths.CTX.make_local()
    monkeypatch.setenv("COLUMNS", "1000")

    assert not run_pipx_cli(["environment", "--verbose"])

    assert (
        f"Both a specific pipx home folder ({paths.CTX.home}) and the fallback pipx home folder ({fallback_home}) "
        "exist. If you are done migrating from the fallback to the new location, it is safe to delete the fallback "
        "location.\n"
    ) in capsys.readouterr().err
