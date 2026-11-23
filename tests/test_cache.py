from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from harness import run_pipx_cli
from pipx.paths import CTX
from pipx.trash import rmdir

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


@pytest.mark.usefixtures("pipx_temp_env")
def test_cache_dir(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["cache", "dir"])

    assert capsys.readouterr().out.strip() == str(CTX.venv_cache)


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        pytest.param(0, "Removed 0 cached environments.\n", id="empty"),
        pytest.param(1, "Removed 1 cached environment.\n", id="one"),
        pytest.param(2, "Removed 2 cached environments.\n", id="multiple"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_cache_purge_removes_run_environments(
    capsys: pytest.CaptureFixture[str],
    count: int,
    expected: str,
) -> None:
    CTX.venv_cache.mkdir(parents=True)
    for index in range(count):
        (CTX.venv_cache / f"cache-{index}").mkdir()

    assert not run_pipx_cli(["cache", "purge"])

    assert (
        capsys.readouterr().out,
        tuple(path for path in CTX.venv_cache.iterdir() if path.is_dir()),
    ) == (expected, ())


@pytest.mark.parametrize("subcommand", [pytest.param("dir", id="dir"), pytest.param("purge", id="purge")])
@pytest.mark.usefixtures("pipx_temp_env")
def test_cache_json_reports_the_directory(
    capsys: pytest.CaptureFixture[str],
    subcommand: str,
) -> None:
    assert not run_pipx_cli(["cache", subcommand, "--output", "json"])

    assert json.loads(capsys.readouterr().out) == {
        "command": ["cache", subcommand],
        "data": {"directory": str(CTX.venv_cache), "removed": []},
        "pipx_result_version": "1",
        "errors": [],
        "exit_code": 0,
        "status": "success",
    }


@pytest.mark.parametrize("subcommand", [pytest.param("dir", id="dir"), pytest.param("purge", id="purge")])
@pytest.mark.usefixtures("pipx_temp_env")
def test_cache_quiet_says_nothing(
    capsys: pytest.CaptureFixture[str],
    subcommand: str,
) -> None:
    assert not run_pipx_cli(["cache", subcommand, "--quiet"])

    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")


@pytest.mark.parametrize(
    ("removed_names", "status"),
    [
        pytest.param([], "error", id="total-failure"),
        pytest.param(["removed-cache"], "partial", id="partial-failure"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_cache_purge_reports_failed_removals(
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
    removed_names: list[str],
    status: str,
) -> None:
    blocked = CTX.venv_cache / "blocked-cache"
    blocked.mkdir(parents=True)
    for removed_name in removed_names:
        (CTX.venv_cache / removed_name).mkdir()

    def remove_if_allowed(path: Path) -> None:
        # rmdir returns without raising when both deletion and moving to the trash fail.
        if path != blocked:
            rmdir(path)

    mocker.patch("pipx.commands.cache.rmdir", side_effect=remove_if_allowed, autospec=True)

    assert run_pipx_cli(["cache", "purge", "--output", "json"]) == 1

    assert json.loads(capsys.readouterr().out) == {
        "command": ["cache", "purge"],
        "data": {"directory": str(CTX.venv_cache), "removed": removed_names},
        "errors": [
            {
                "code": "cache_purge_failed",
                "environment": blocked.name,
                "message": f"Failed to remove cached environment {blocked}.",
                "package": None,
            },
        ],
        "exit_code": 1,
        "pipx_result_version": "1",
        "status": status,
    }
    assert {path.name for path in CTX.venv_cache.iterdir() if path.is_dir()} == {blocked.name}


@pytest.mark.parametrize(
    ("quiet_args", "expected_stdout"),
    [
        pytest.param([], "Removed 0 cached environments.\n", id="normal"),
        pytest.param(["--quiet"], "", id="quiet"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_cache_purge_reports_failure_in_text(
    capsys: pytest.CaptureFixture[str], mocker: MockerFixture, quiet_args: list[str], expected_stdout: str
) -> None:
    blocked = CTX.venv_cache / "blocked-cache"
    blocked.mkdir(parents=True)
    mocker.patch("pipx.commands.cache.rmdir", autospec=True)

    assert run_pipx_cli(["cache", "purge", *quiet_args]) == 1

    captured = capsys.readouterr()
    assert (captured.out, captured.err) == (expected_stdout, f"Failed to remove cached environment {blocked}.\n")


@pytest.mark.usefixtures("pipx_temp_env")
def test_cache_purge_counts_environment_moved_to_trash(
    capsys: pytest.CaptureFixture[str], mocker: MockerFixture
) -> None:
    cached = CTX.venv_cache / "cached-environment"
    cached.mkdir(parents=True)
    mocker.patch("pipx.trash.shutil.rmtree", autospec=True)

    assert not run_pipx_cli(["cache", "purge", "--output", "json"])

    result = json.loads(capsys.readouterr().out)
    assert (result["status"], result["errors"], result["data"]["removed"]) == ("success", [], [cached.name])
    assert not cached.exists()
    assert len(list(CTX.trash.glob(f"*.{cached.name}"))) == 1
