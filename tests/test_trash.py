from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Final

from pipx import paths
from pipx.trash import rmdir, rmdir_via_trash, safe_unlink

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    import pytest
    from pytest_mock import MockerFixture


def test_rmdir_without_safe_rm_is_non_fatal_for_locked_files(
    caplog: pytest.LogCaptureFixture,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    (locked_dir := tmp_path / "locked").mkdir()
    (locked_dir / "locked.dll").write_text("locked")
    rmtree: Final[MagicMock] = mocker.patch("pipx.trash.shutil.rmtree", autospec=True)

    with caplog.at_level(logging.WARNING, logger="pipx.trash"):
        rmdir(locked_dir, safe_rm=False)

    rmtree.assert_called_once_with(locked_dir, ignore_errors=True)
    assert locked_dir.is_dir()
    assert f"Failed to delete {locked_dir}. You may need to delete it manually." in caplog.text


def test_rmdir_with_safe_rm_is_non_fatal_when_move_fails(
    caplog: pytest.LogCaptureFixture,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    (path := tmp_path / "locked").mkdir()
    mocker.patch("pipx.trash.shutil.rmtree", autospec=True)
    mocker.patch.object(Path, "rename", side_effect=PermissionError("locked directory"))
    mocker.patch.object(type(paths.CTX), "trash", mocker.PropertyMock(return_value=tmp_path / "trash"))

    with caplog.at_level(logging.WARNING, logger="pipx.trash"):
        rmdir(path)

    assert path.is_dir()
    assert f"Failed to move {path} to the trash" in caplog.text


def test_rmdir_via_trash_removes_in_place_when_the_move_fails(mocker: MockerFixture, tmp_path: Path) -> None:
    (path := tmp_path / "venv").mkdir()
    mocker.patch.object(Path, "rename", autospec=True, side_effect=OSError("cross-device link"))
    mocker.patch.object(type(paths.CTX), "trash", mocker.PropertyMock(return_value=tmp_path / "trash"))

    rmdir_via_trash(path)

    assert sorted(entry.name for entry in tmp_path.iterdir()) == ["trash"]


def test_safe_unlink_handles_existing_trash_directory(mocker: MockerFixture, tmp_path: Path) -> None:
    (file := tmp_path / "locked").write_text("content")
    (trash_dir := tmp_path / "trash").mkdir()
    mocker.patch.object(type(paths.CTX), "trash", mocker.PropertyMock(return_value=trash_dir))
    mocker.patch.object(Path, "unlink", side_effect=PermissionError("locked file"))

    safe_unlink(file)

    assert not file.exists()
    assert [path.read_text() for path in trash_dir.iterdir()] == ["content"]
