from __future__ import annotations

import json
from typing import TYPE_CHECKING, Final

import pytest

from helpers import run_pipx_cli
from pipx import paths

if TYPE_CHECKING:
    from _pytest.capture import CaptureResult


def test_cache_dir(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["cache", "dir"])

    assert capsys.readouterr().out.strip() == str(paths.ctx.venv_cache)


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        pytest.param(0, "Removed 0 cached environments.\n", id="empty"),
        pytest.param(1, "Removed 1 cached environment.\n", id="one"),
        pytest.param(2, "Removed 2 cached environments.\n", id="multiple"),
    ],
)
def test_cache_purge_removes_run_environments(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
    count: int,
    expected: str,
) -> None:
    cache_names: Final[tuple[str, ...]] = tuple(f"cache-{index}" for index in range(count))
    paths.ctx.venv_cache.mkdir(parents=True)
    for cache_name in cache_names:
        (paths.ctx.venv_cache / cache_name).mkdir()

    assert not run_pipx_cli(["cache", "purge"])

    assert (
        capsys.readouterr().out,
        tuple(path for path in paths.ctx.venv_cache.iterdir() if path.is_dir()),
    ) == (expected, ())


@pytest.mark.parametrize(
    ("subcommand", "command"),
    [
        pytest.param("dir", "cache-dir", id="dir"),
        pytest.param("purge", "cache-purge", id="purge"),
    ],
)
def test_cache_json_reports_the_directory(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
    subcommand: str,
    command: str,
) -> None:
    assert not run_pipx_cli(["cache", subcommand, "--output", "json"])

    assert json.loads(capsys.readouterr().out) == {
        "command": command,
        "data": {"directory": str(paths.ctx.venv_cache), "removed": []},
        "pipx_result_version": "0.1",
        "status": "success",
    }


@pytest.mark.parametrize("subcommand", [pytest.param("dir", id="dir"), pytest.param("purge", id="purge")])
def test_cache_quiet_says_nothing(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
    subcommand: str,
) -> None:
    assert not run_pipx_cli(["cache", subcommand, "--quiet"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")
