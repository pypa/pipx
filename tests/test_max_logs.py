"""Tests for PIPX_MAX_LOGS environment variable functionality."""

from __future__ import annotations

import errno
from typing import TYPE_CHECKING, Final, cast

import pytest

from helpers import run_pipx_cli
from pipx import constants, main, paths

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


@pytest.fixture
def log_dir() -> Path:
    paths.ctx.logs.mkdir(parents=True)
    return paths.ctx.logs


@pytest.mark.parametrize(
    ("max_logs", "existing", "expected"),
    [
        pytest.param(None, 15, 10, id="default"),
        pytest.param("5", 15, 5, id="env-var"),
        pytest.param("100", 5, 6, id="under-limit"),
        pytest.param("1", 15, 1, id="one"),
        pytest.param("0", 15, 1, id="zero-keeps-current-run"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_max_logs_counts_the_new_log(
    log_dir: Path, monkeypatch: pytest.MonkeyPatch, max_logs: str | None, existing: int, expected: int
) -> None:
    if max_logs is None:
        monkeypatch.delenv("PIPX_MAX_LOGS", raising=False)
    else:
        monkeypatch.setenv("PIPX_MAX_LOGS", max_logs)
    for i in range(existing):
        (log_dir / f"cmd_2024-01-01_00.00.{i:02d}.log").touch()

    assert not run_pipx_cli(["list"])

    assert len(list(log_dir.glob("cmd_*[0-9].log"))) == expected


@pytest.mark.usefixtures("pipx_temp_env")
def test_max_logs_rotates_every_backend_error_log(log_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIPX_MAX_LOGS", "2")
    for i, backend in enumerate(["uv", "pip", "uv", "pip"]):
        (log_dir / f"cmd_2024-01-01_00.00.{i:02d}_{backend}_errors.log").touch()

    assert not run_pipx_cli(["list"])

    assert sorted(path.name for path in log_dir.glob("cmd_*_errors.log")) == ["cmd_2024-01-01_00.00.03_pip_errors.log"]


@pytest.mark.usefixtures("pipx_temp_env")
def test_max_logs_orders_same_second_logs_by_counter(log_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIPX_MAX_LOGS", "2")
    for counter in ("", "_1"):
        (log_dir / f"cmd_2024-01-01_00.00.00{counter}_uv_errors.log").touch()

    assert not run_pipx_cli(["list"])

    assert [path.name for path in log_dir.glob("cmd_*_errors.log")] == ["cmd_2024-01-01_00.00.00_1_uv_errors.log"]


@pytest.mark.usefixtures("pipx_temp_env")
def test_max_logs_keeps_logs_of_running_command(log_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIPX_MAX_LOGS", "1")
    assert not run_pipx_cli(["list"])
    # the first command's log handler stays open until the next command replaces it, like a concurrent pipx process
    log: Final[Path] = cast("Path", paths.ctx.log_file)
    (error_log := log.with_name(f"{log.stem}_uv_errors.log")).touch()

    assert not run_pipx_cli(["list"])

    assert {log, error_log} <= set(log_dir.iterdir())


@pytest.mark.parametrize(
    ("raw", "expected_logs", "expected_invalid"),
    [
        pytest.param(None, 10, False, id="unset"),
        pytest.param("", 10, False, id="empty"),
        pytest.param("   ", 10, False, id="whitespace-only"),
        pytest.param("10", 10, False, id="default"),
        pytest.param(" 5 ", 5, False, id="whitespace-padded"),
        pytest.param("0", 0, False, id="zero"),
        pytest.param("-1", 10, True, id="negative"),
        pytest.param("garbage", 10, True, id="not-an-integer"),
    ],
)
def test_compute_max_logs(raw: str | None, expected_logs: int, expected_invalid: bool) -> None:
    assert constants._compute_max_logs(raw) == (expected_logs, expected_invalid)  # ruff:ignore[private-member-access]  # no public API


def test_cli_rejects_invalid_env_max_logs(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(main, "_MAX_LOGS_INVALID", True)
    monkeypatch.setattr(main, "_MAX_LOGS_RAW", "garbage")

    assert run_pipx_cli(["list"])

    assert "PIPX_MAX_LOGS must be unset or a non-negative integer, got 'garbage'." in capsys.readouterr().err


@pytest.mark.parametrize("raw", ["", "   "], ids=["empty", "whitespace-only"])
@pytest.mark.usefixtures("pipx_temp_env")
def test_cli_blank_env_max_logs_falls_back_to_default(
    raw: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Blank values pass validation as unset, so log setup must not re-crash on a raw int() parse."""
    monkeypatch.setenv("PIPX_MAX_LOGS", raw)

    assert not run_pipx_cli(["list"])

    assert "ValueError" not in capsys.readouterr().err


@pytest.mark.skipif(constants.WINDOWS, reason="file locks only guard logs on POSIX")
@pytest.mark.usefixtures("pipx_temp_env")
def test_max_logs_rotates_without_lock_support(
    log_dir: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    monkeypatch.setenv("PIPX_MAX_LOGS", "1")
    (log_dir / "cmd_2024-01-01_00.00.00.log").touch()
    mocker.patch("fcntl.flock", side_effect=OSError(errno.ENOLCK, "No locks available"))

    assert not run_pipx_cli(["list"])

    assert [path.name for path in log_dir.glob("cmd_*.log")] == [cast("Path", paths.ctx.log_file).name]
