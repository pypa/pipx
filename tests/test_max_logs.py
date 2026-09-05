"""Tests for PIPX_MAX_LOGS environment variable functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from helpers import run_pipx_cli
from pipx import constants, main
from pipx.main import (
    _setup_log_file,  # ruff:ignore[import-private-name]  # test exercises private helper, no public API
    delete_oldest_logs,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_delete_oldest_logs_keeps_specified_number(tmp_path: Path) -> None:
    """Test that delete_oldest_logs keeps only the specified number of newest files."""
    # Create 5 log files
    log_files = []
    for i in range(5):
        log_file = tmp_path / f"cmd_2024-01-01_00.00.0{i}.log"
        log_file.touch()
        log_files.append(log_file)

    # Keep only 2
    delete_oldest_logs(log_files, keep_number=2)

    # Check that only the 2 newest files remain
    remaining = list(tmp_path.glob("cmd_*.log"))
    assert len(remaining) == 2


def test_delete_oldest_logs_keeps_none(tmp_path: Path) -> None:
    """Test that delete_oldest_logs with keep_number=0 deletes every file."""
    log_files = []
    for i in range(5):
        log_file = tmp_path / f"cmd_2024-01-01_00.00.0{i}.log"
        log_file.touch()
        log_files.append(log_file)

    delete_oldest_logs(log_files, keep_number=0)

    remaining = list(tmp_path.glob("cmd_*.log"))
    assert remaining == []


def test_max_logs_zero_keeps_only_the_new_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that PIPX_MAX_LOGS=0 prunes the existing logs."""
    monkeypatch.setenv("PIPX_MAX_LOGS", "0")

    for i in range(15):
        log_file = tmp_path / f"cmd_2024-01-01_00.00.{i:02d}.log"
        log_file.touch()

    _setup_log_file(pipx_log_dir=tmp_path)

    # Every pre-existing log is pruned, leaving only the one just created.
    remaining = list(tmp_path.glob("cmd_*.log"))
    assert len(remaining) == 1


def test_delete_oldest_logs_keeps_all_when_under_limit(tmp_path: Path) -> None:
    """Test that delete_oldest_logs keeps all files when under the limit."""
    log_files = []
    for i in range(3):
        log_file = tmp_path / f"cmd_2024-01-01_00.00.0{i}.log"
        log_file.touch()
        log_files.append(log_file)

    delete_oldest_logs(log_files, keep_number=10)

    remaining = list(tmp_path.glob("cmd_*.log"))
    assert len(remaining) == 3


def test_max_logs_defaults_to_10(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that max_logs defaults to 10 when PIPX_MAX_LOGS is not set."""
    monkeypatch.delenv("PIPX_MAX_LOGS", raising=False)

    # Create 15 log files
    for i in range(15):
        log_file = tmp_path / f"cmd_2024-01-01_00.00.{i:02d}.log"
        log_file.touch()

    _setup_log_file(pipx_log_dir=tmp_path)

    # Should have 10 old logs + 1 new log = 11 total
    remaining = list(tmp_path.glob("cmd_*.log"))
    assert len(remaining) == 11


def test_max_logs_respects_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that max_logs respects the PIPX_MAX_LOGS environment variable."""
    monkeypatch.setenv("PIPX_MAX_LOGS", "5")

    # Create 15 log files
    for i in range(15):
        log_file = tmp_path / f"cmd_2024-01-01_00.00.{i:02d}.log"
        log_file.touch()

    _setup_log_file(pipx_log_dir=tmp_path)

    # Should have 5 old logs + 1 new log = 6 total
    remaining = list(tmp_path.glob("cmd_*.log"))
    assert len(remaining) == 6


def test_max_logs_with_large_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that a large PIPX_MAX_LOGS value keeps all logs."""
    monkeypatch.setenv("PIPX_MAX_LOGS", "100")

    # Create 5 log files
    for i in range(5):
        log_file = tmp_path / f"cmd_2024-01-01_00.00.0{i}.log"
        log_file.touch()

    _setup_log_file(pipx_log_dir=tmp_path)

    # Should have 5 old logs + 1 new log = 6 total
    remaining = list(tmp_path.glob("cmd_*.log"))
    assert len(remaining) == 6


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
def test_cli_blank_env_max_logs_falls_back_to_default(
    raw: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Blank values pass validation as unset, so log setup must not re-crash on a raw int() parse."""
    monkeypatch.setenv("PIPX_MAX_LOGS", raw)

    assert not run_pipx_cli(["list"])

    assert "ValueError" not in capsys.readouterr().err
