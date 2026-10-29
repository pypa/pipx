from __future__ import annotations

import errno
import os
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from helpers import current_log_file, run_pipx_cli
from pipx import constants, main, paths

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    ("environment", "existing", "expected"),
    [
        pytest.param({}, 15, 10, id="default"),
        pytest.param({"PIPX_MAX_LOGS": "5"}, 15, 5, id="env-var"),
        pytest.param({"PIPX_MAX_LOGS": "100"}, 5, 6, id="under-limit"),
        pytest.param({"PIPX_MAX_LOGS": "1"}, 15, 1, id="one"),
        pytest.param({"PIPX_MAX_LOGS": "0"}, 15, 1, id="zero-keeps-current-run"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_max_logs_counts_the_new_log(
    log_dir: Path, monkeypatch: pytest.MonkeyPatch, environment: dict[str, str], existing: int, expected: int
) -> None:
    monkeypatch.delenv("PIPX_MAX_LOGS", raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    for index in range(existing):
        (log_dir / f"cmd_2024-01-01_00.00.{index:02d}.log").touch()

    assert not run_pipx_cli(["list"])

    assert len(list(log_dir.glob("cmd_*[0-9].log"))) == expected


@pytest.fixture
def log_dir() -> Path:
    paths.CTX.logs.mkdir(parents=True)
    return paths.CTX.logs


@pytest.mark.usefixtures("pipx_temp_env")
def test_max_logs_rotates_every_backend_error_log(log_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIPX_MAX_LOGS", "2")
    for index, backend in enumerate(["uv", "pip", "uv", "pip"]):
        (log_dir / f"cmd_2024-01-01_00.00.{index:02d}_{backend}_errors.log").touch()

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
    log: Final[Path] = current_log_file()
    (error_log := log.with_name(f"{log.stem}_uv_errors.log")).touch()

    assert not run_pipx_cli(["list"])

    assert {log, error_log} <= set(log_dir.iterdir())


def test_cli_rejects_invalid_env_max_logs(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(main, "MAX_LOGS_INVALID", True)
    monkeypatch.setattr(main, "MAX_LOGS_RAW", "garbage")

    assert run_pipx_cli(["list"])

    assert "PIPX_MAX_LOGS must be unset or a non-negative integer, got 'garbage'." in capsys.readouterr().err


@pytest.mark.parametrize("raw", [pytest.param("", id="empty"), pytest.param("   ", id="whitespace-only")])
@pytest.mark.usefixtures("pipx_temp_env")
def test_cli_blank_env_max_logs_falls_back_to_default(
    raw: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # blank values pass validation as unset, so the log setup must not parse them with int() again
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

    assert [path.name for path in log_dir.glob("cmd_*.log")] == [current_log_file().name]


@pytest.mark.skipif(constants.WINDOWS, reason="POSIX permission bits decide whether the log can be opened")
@pytest.mark.skipif(not constants.WINDOWS and os.geteuid() == 0, reason="root reads any file")
@pytest.mark.usefixtures("pipx_temp_env")
def test_max_logs_rotates_an_unreadable_log(log_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIPX_MAX_LOGS", "1")
    (unreadable := log_dir / "cmd_2024-01-01_00.00.00.log").touch()
    unreadable.chmod(0)

    assert not run_pipx_cli(["list"])

    assert [path.name for path in log_dir.glob("cmd_*.log")] == [current_log_file().name]


@pytest.mark.skipif(constants.WINDOWS, reason="creating symlinks needs developer mode on Windows")
@pytest.mark.parametrize(
    "target",
    [pytest.param("cmd_2024-01-01_00.00.00.log", id="symlink-loop"), pytest.param(".", id="symlink-to-dir")],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_max_logs_rotates_a_log_that_cannot_open(log_dir: Path, monkeypatch: pytest.MonkeyPatch, target: str) -> None:
    monkeypatch.setenv("PIPX_MAX_LOGS", "1")
    (log_dir / "cmd_2024-01-01_00.00.00.log").symlink_to(target)

    assert not run_pipx_cli(["list"])

    assert [path.name for path in log_dir.glob("cmd_*.log")] == [current_log_file().name]


@pytest.mark.parametrize(
    "name",
    [
        pytest.param("cmd_2024-01-01_00.00.00.log", id="command-log"),
        pytest.param("cmd_2024-01-01_00.00.00_uv_errors.log", id="error-log"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_max_logs_keeps_logging_beside_a_log_it_cannot_remove(
    log_dir: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, name: str
) -> None:
    monkeypatch.setenv("PIPX_MAX_LOGS", "1")
    (log_dir / name).touch()
    # a sticky shared directory lets this user create a log but not remove another user's
    mocker.patch.object(Path, "unlink", autospec=True, side_effect=PermissionError(errno.EPERM, "Not permitted"))

    assert not run_pipx_cli(["list"])

    assert current_log_file().parent == log_dir
