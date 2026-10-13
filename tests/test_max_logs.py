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
def test_max_logs_counts_the_new_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, max_logs: str | None, existing: int, expected: int
) -> None:
    if max_logs is None:
        monkeypatch.delenv("PIPX_MAX_LOGS", raising=False)
    else:
        monkeypatch.setenv("PIPX_MAX_LOGS", max_logs)
    for i in range(existing):
        (tmp_path / f"cmd_2024-01-01_00.00.{i:02d}.log").touch()

    _setup_log_file(pipx_log_dir=tmp_path)

    assert len(list(tmp_path.glob("cmd_*[0-9].log"))) == expected


def test_max_logs_rotates_every_backend_error_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIPX_MAX_LOGS", "2")
    for i, backend in enumerate(["uv", "pip", "uv", "pip"]):
        (tmp_path / f"cmd_2024-01-01_00.00.{i:02d}_{backend}_errors.log").touch()

    _setup_log_file(pipx_log_dir=tmp_path)

    assert sorted(path.name for path in tmp_path.glob("cmd_*_errors.log")) == ["cmd_2024-01-01_00.00.03_pip_errors.log"]


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
