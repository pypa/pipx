from __future__ import annotations

import json
from typing import TYPE_CHECKING, Final

import pytest

from helpers import app_name, run_pipx_cli
from pipx import paths

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


@pytest.fixture
def installed_pycowsay(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()


def test_reset_removes_the_installed_packages(
    installed_pycowsay: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["reset", "--force"])
    capsys.readouterr()

    assert not run_pipx_cli(["list", "--short"])

    assert capsys.readouterr().out == ""


def test_reset_unlinks_the_apps(installed_pycowsay: None) -> None:
    app: Final[Path] = paths.ctx.bin_dir / app_name("pycowsay")
    assert app.exists() or app.is_symlink()

    assert not run_pipx_cli(["reset", "--force"])

    assert not app.exists() and not app.is_symlink()


@pytest.mark.parametrize(
    "location",
    [
        pytest.param("venvs", id="venvs"),
        pytest.param("venv_cache", id="cache"),
        pytest.param("standalone_python_cachedir", id="interpreters"),
    ],
)
def test_reset_removes_the_pipx_state(installed_pycowsay: None, location: str) -> None:
    target: Final[Path] = getattr(paths.ctx, location)
    target.mkdir(parents=True, exist_ok=True)

    assert not run_pipx_cli(["reset", "--force"])

    assert not target.is_dir()


def test_reset_keeps_the_log_it_writes(installed_pycowsay: None) -> None:
    stale: Final[Path] = paths.ctx.logs / "cmd_stale.log"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.touch()

    assert not run_pipx_cli(["reset", "--force"])

    assert list(paths.ctx.logs.iterdir()) == [paths.ctx.log_file]


def test_reset_dry_run_keeps_everything(
    installed_pycowsay: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["reset", "--dry-run"])
    assert f"Would remove {paths.ctx.venvs}" in capsys.readouterr().out

    assert not run_pipx_cli(["list", "--short"])

    assert capsys.readouterr().out == "pycowsay 0.0.0.2\n"


def test_reset_json_reports_what_it_removed(
    installed_pycowsay: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["reset", "--force", "--output", "json"])

    assert json.loads(capsys.readouterr().out) == {
        "command": "reset",
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
        "pipx_result_version": "0.1",
        "status": "success",
    }


def test_reset_without_a_terminal_demands_force(
    installed_pycowsay: None,
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    mocker.patch("pipx.main.sys.stdin.isatty", return_value=False)

    assert run_pipx_cli(["reset"])

    assert "Pass --force to reset" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("answer", "resets"),
    [
        pytest.param("y", True, id="y"),
        pytest.param("Yes", True, id="yes"),
        pytest.param("", False, id="empty"),
        pytest.param("n", False, id="n"),
    ],
)
def test_reset_asks_before_it_removes(
    installed_pycowsay: None,
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
    answer: str,
    resets: bool,
) -> None:
    mocker.patch("pipx.main.sys.stdin.isatty", return_value=True)
    mocker.patch("pipx.main.input", return_value=answer)

    assert bool(run_pipx_cli(["reset"])) is not resets

    assert paths.ctx.venvs.is_dir() is not resets
