from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from pipx import paths
from pipx.util import rmdir, run_subprocess, safe_unlink

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_rmdir_without_safe_rm_is_non_fatal_for_locked_files(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    trash_dir = tmp_path / "trash"
    trash_dir.mkdir()
    (trash_dir / "locked.dll").write_text("locked")

    def fake_rmtree(path: Path, ignore_errors: bool = False) -> None:
        assert path == trash_dir
        if not ignore_errors:
            raise PermissionError("locked file")

    monkeypatch.setattr("pipx.util.shutil.rmtree", fake_rmtree)

    with caplog.at_level(logging.WARNING, logger="pipx.util"):
        rmdir(trash_dir, safe_rm=False)

    assert trash_dir.is_dir()
    assert f"Failed to delete {trash_dir}. You may need to delete it manually." in caplog.text


def test_rmdir_with_safe_rm_is_non_fatal_when_move_fails(
    caplog: pytest.LogCaptureFixture,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    path = tmp_path / "locked"
    path.mkdir()
    mocker.patch("pipx.util.shutil.rmtree")
    mocker.patch.object(Path, "rename", side_effect=PermissionError("locked directory"))
    mocker.patch.object(type(paths.ctx), "trash", mocker.PropertyMock(return_value=tmp_path / "trash"))

    with caplog.at_level(logging.WARNING, logger="pipx.util"):
        rmdir(path)

    assert path.is_dir()
    assert f"Failed to move {path} to the trash" in caplog.text


def test_safe_unlink_handles_existing_trash_directory(mocker: MockerFixture, tmp_path: Path) -> None:
    file = tmp_path / "locked"
    file.write_text("content")
    trash_dir = tmp_path / "trash"
    trash_dir.mkdir()
    is_dir = Path.is_dir
    stale = True

    def stale_is_dir(path: Path) -> bool:
        nonlocal stale
        if path == trash_dir and stale:
            stale = False
            return False
        return is_dir(path)

    mocker.patch.object(type(paths.ctx), "trash", mocker.PropertyMock(return_value=trash_dir))
    mocker.patch.object(Path, "is_dir", stale_is_dir)
    mocker.patch.object(Path, "unlink", side_effect=PermissionError("locked file"))

    safe_unlink(file)

    assert not file.exists()
    assert [path.read_text() for path in trash_dir.iterdir()] == ["content"]


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        pytest.param(None, "subprocess", id="defaults_to_subprocess"),
        pytest.param("import", "import", id="preserves_explicit"),
    ],
)
def test_subprocess_keyring_provider(monkeypatch: pytest.MonkeyPatch, env_value: str | None, expected: str) -> None:
    if env_value is not None:
        monkeypatch.setenv("PIP_KEYRING_PROVIDER", env_value)
    else:
        monkeypatch.delenv("PIP_KEYRING_PROVIDER", raising=False)

    result = run_subprocess([sys.executable, "-c", "import os; print(os.environ['PIP_KEYRING_PROVIDER'])"])

    assert result.stdout.strip() == expected


def test_subprocess_pythonsafepath_set_for_python_commands() -> None:
    """Test that PYTHONSAFEPATH is set for Python subprocess calls to prevent CWD shadowing (issue #1575)."""
    result = run_subprocess(
        [sys.executable, "-c", "import os, sys; sys.stdout.write(os.environ.get('PYTHONSAFEPATH', ''))"]
    )

    assert result.stdout == "1"
