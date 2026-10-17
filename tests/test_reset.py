from __future__ import annotations

import json
from io import StringIO
from typing import TYPE_CHECKING, Final

import pytest

from helpers import app_name, run_pipx_cli
from pipx import paths

if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.capture import CaptureResult
    from pytest_mock import MockerFixture


@pytest.fixture
def installed_pycowsay(
    request: pytest.FixtureRequest,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    request.getfixturevalue("pipx_temp_env")
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()
    # reset deletes the shared libraries; point it at a stand-in so the worker's session copy, which every later test
    # reuses, does not have to be rebuilt
    (shared_libs := tmp_path / "reset-shared-libs").mkdir()
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_SHARED_LIBS", shared_libs)
    paths.ctx.make_local()


@pytest.fixture
def interactive_stdin(mocker: MockerFixture) -> StringIO:
    stream: Final[StringIO] = StringIO()
    mocker.patch("pipx.main.sys.stdin", new=stream)
    mocker.patch.object(stream, "isatty", return_value=True)
    return stream


@pytest.mark.usefixtures("installed_pycowsay")
def test_reset_removes_the_installed_packages(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["reset", "--yes"])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "--short"])

    assert not capsys.readouterr().out


@pytest.mark.usefixtures("installed_pycowsay")
def test_reset_unlinks_the_apps() -> None:
    app: Final[Path] = paths.ctx.bin_dir / app_name("pycowsay")
    assert app.exists() or app.is_symlink()

    assert not run_pipx_cli(["reset", "--yes"])

    assert not app.exists()
    assert not app.is_symlink()


@pytest.mark.parametrize(
    "location",
    [
        pytest.param("venvs", id="venvs"),
        pytest.param("venv_cache", id="cache"),
        pytest.param("standalone_python_cachedir", id="interpreters"),
    ],
)
@pytest.mark.usefixtures("installed_pycowsay")
def test_reset_removes_the_pipx_state(location: str) -> None:
    target: Final[Path] = getattr(paths.ctx, location)
    target.mkdir(parents=True, exist_ok=True)

    assert not run_pipx_cli(["reset", "--yes"])

    assert not target.is_dir()


@pytest.mark.usefixtures("installed_pycowsay")
def test_reset_keeps_the_log_it_writes() -> None:
    stale: Final[Path] = paths.ctx.logs / "cmd_stale.log"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.touch()

    assert not run_pipx_cli(["reset", "--yes"])

    assert list(paths.ctx.logs.iterdir()) == [paths.ctx.log_file]


@pytest.mark.usefixtures("installed_pycowsay")
def test_reset_dry_run_keeps_everything(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["reset", "--dry-run"])
    reported: Final[str] = capsys.readouterr().out
    assert f"Would remove {paths.ctx.venvs}" in reported
    assert f"Would remove {paths.ctx.bin_dir / app_name('pycowsay')}" in reported

    assert not run_pipx_cli(["list", "--short"])

    assert capsys.readouterr().out == "pycowsay 0.0.0.2\n"


@pytest.mark.usefixtures("installed_pycowsay")
def test_reset_json_reports_what_it_removed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["reset", "--yes", "--output", "json"])

    assert json.loads(capsys.readouterr().out) == {
        "command": ["reset"],
        "data": {
            "packages": ["pycowsay"],
            "removed": [
                str(paths.ctx.venvs),
                str(paths.ctx.shared_libs),
                str(paths.ctx.venv_cache),
                str(paths.ctx.standalone_python_cachedir),
                str(paths.ctx.logs),
            ],
        },
        "pipx_result_version": "1",
        "errors": [],
        "exit_code": 0,
        "status": "success",
    }


@pytest.mark.usefixtures("installed_pycowsay")
def test_reset_without_a_terminal_demands_force(
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    mocker.patch("pipx.main.sys.stdin.isatty", return_value=False)

    assert run_pipx_cli(["reset"])

    assert "Pass --yes to reset" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("answer", "resets"),
    [
        pytest.param("y", True, id="y"),
        pytest.param("Yes", True, id="yes"),
        pytest.param("", False, id="empty"),
        pytest.param("n", False, id="n"),
    ],
)
@pytest.mark.usefixtures("installed_pycowsay")
def test_reset_asks_before_it_removes(
    mocker: MockerFixture,
    answer: str,
    resets: bool,
) -> None:
    mocker.patch("pipx.main.sys.stdin.isatty", return_value=True)
    mocker.patch("pipx.main.input", return_value=answer)

    assert bool(run_pipx_cli(["reset"])) is not resets

    assert paths.ctx.venvs.is_dir() is not resets


@pytest.mark.usefixtures("installed_pycowsay", "interactive_stdin")
def test_reset_eof_cancels(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["reset"]) == 1

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert "Reset cancelled." in captured.err
    assert paths.ctx.venvs.is_dir()


@pytest.mark.usefixtures("installed_pycowsay", "interactive_stdin")
def test_reset_eof_reports_json_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["reset", "--output", "json"]) == 1

    assert json.loads(capsys.readouterr().out) == {
        "command": ["reset"],
        "data": {},
        "errors": [
            {
                "code": "pipx_error",
                "environment": None,
                "message": "Reset cancelled.",
                "package": None,
            }
        ],
        "exit_code": 1,
        "pipx_result_version": "1",
        "status": "error",
    }
    assert paths.ctx.venvs.is_dir()


@pytest.mark.usefixtures("installed_pycowsay")
def test_reset_confirmed_json_keeps_prompt_off_stdout(
    capsys: pytest.CaptureFixture[str],
    interactive_stdin: StringIO,
) -> None:
    interactive_stdin.write("y\n")
    interactive_stdin.seek(0)

    assert run_pipx_cli(["reset", "--output", "json"]) == 0

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert json.loads(captured.out)["status"] == "success"
    assert "Remove every pipx-installed package" in captured.err
    assert not paths.ctx.venvs.is_dir()
