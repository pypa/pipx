"""Tests for MAX_PIPX_LOGS environment variable functionality."""

from pipx.main import _setup_log_file, delete_oldest_logs


def test_delete_oldest_logs_keeps_specified_number(tmp_path):
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


def test_delete_oldest_logs_keeps_all_when_under_limit(tmp_path):
    """Test that delete_oldest_logs keeps all files when under the limit."""
    log_files = []
    for i in range(3):
        log_file = tmp_path / f"cmd_2024-01-01_00.00.0{i}.log"
        log_file.touch()
        log_files.append(log_file)

    delete_oldest_logs(log_files, keep_number=10)

    remaining = list(tmp_path.glob("cmd_*.log"))
    assert len(remaining) == 3


def test_max_logs_defaults_to_10(tmp_path, monkeypatch):
    """Test that max_logs defaults to 10 when MAX_PIPX_LOGS is not set."""
    monkeypatch.delenv("MAX_PIPX_LOGS", raising=False)

    # Create 15 log files
    for i in range(15):
        log_file = tmp_path / f"cmd_2024-01-01_00.00.{i:02d}.log"
        log_file.touch()

    _setup_log_file(pipx_log_dir=tmp_path)

    # Should have 10 old logs + 1 new log = 11 total
    remaining = list(tmp_path.glob("cmd_*.log"))
    assert len(remaining) == 11


def test_max_logs_respects_env_var(tmp_path, monkeypatch):
    """Test that max_logs respects the MAX_PIPX_LOGS environment variable."""
    monkeypatch.setenv("MAX_PIPX_LOGS", "5")

    # Create 15 log files
    for i in range(15):
        log_file = tmp_path / f"cmd_2024-01-01_00.00.{i:02d}.log"
        log_file.touch()

    _setup_log_file(pipx_log_dir=tmp_path)

    # Should have 5 old logs + 1 new log = 6 total
    remaining = list(tmp_path.glob("cmd_*.log"))
    assert len(remaining) == 6


def test_max_logs_with_large_value(tmp_path, monkeypatch):
    """Test that a large MAX_PIPX_LOGS value keeps all logs."""
    monkeypatch.setenv("MAX_PIPX_LOGS", "100")

    # Create 5 log files
    for i in range(5):
        log_file = tmp_path / f"cmd_2024-01-01_00.00.0{i}.log"
        log_file.touch()

    _setup_log_file(pipx_log_dir=tmp_path)

    # Should have 5 old logs + 1 new log = 6 total
    remaining = list(tmp_path.glob("cmd_*.log"))
    assert len(remaining) == 6
