import sys
from unittest import mock

import pytest  # type: ignore[import-not-found]

from helpers import run_pipx_cli
from pipx import main


def test_help_text(monkeypatch, capsys):
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(ValueError, match="raised in test to exit early"):
        assert not run_pipx_cli(["--help"])
    captured = capsys.readouterr()
    assert "usage: pipx" in captured.out


def test_version(monkeypatch, capsys):
    mock_exit = mock.Mock(side_effect=ValueError("raised in test to exit early"))
    with mock.patch.object(sys, "exit", mock_exit), pytest.raises(ValueError, match="raised in test to exit early"):
        assert not run_pipx_cli(["--version"])
    captured = capsys.readouterr()
    mock_exit.assert_called_with(0)
    assert main.__version__ in captured.out.strip()


@pytest.mark.parametrize(
    ("argv", "executable", "expected"),
    [
        ("/usr/bin/pipx", "", "pipx"),
        ("__main__.py", "/usr/bin/python", "/usr/bin/python -m pipx"),
    ],
)
def test_prog_name(monkeypatch, argv, executable, expected):
    monkeypatch.setattr("pipx.main.sys.argv", [argv])
    monkeypatch.setattr("pipx.main.sys.executable", executable)
    assert main.prog_name() == expected


def test_limit_verbosity():
    assert not run_pipx_cli(["list", "-qqq"])
    assert not run_pipx_cli(["list", "-vvvv"])


def test_max_pipx_logs_env_var(tmp_path, monkeypatch):
    """Test that MAX_PIPX_LOGS environment variable is respected."""
    from pipx.main import _setup_log_file

    log_dir = tmp_path / "logs"

    # Create some existing log files
    log_dir.mkdir(parents=True, exist_ok=True)
    for i in range(15):
        (log_dir / f"cmd_2026-03-14_12.00.{i:02d}.log").touch()

    # Test default value (10)
    monkeypatch.delenv("MAX_PIPX_LOGS", raising=False)
    remaining_before = len(list(log_dir.glob("cmd_*.log")))
    assert remaining_before == 15

    # When setup_log_file runs with default, it should keep 10 logs
    _setup_log_file(log_dir)
    remaining_after = len(list(log_dir.glob("cmd_*.log")))
    assert remaining_after == 11  # 10 old + 1 new

    # Clean up and test with custom env var
    for f in log_dir.glob("cmd_*.log"):
        f.unlink()
    for i in range(20):
        (log_dir / f"cmd_2026-03-14_13.00.{i:02d}.log").touch()

    # Test with MAX_PIPX_LOGS=5
    monkeypatch.setenv("MAX_PIPX_LOGS", "5")
    _setup_log_file(log_dir)
    remaining = len(list(log_dir.glob("cmd_*.log")))
    assert remaining == 6  # 5 old + 1 new
