from __future__ import annotations

from contextlib import contextmanager
from threading import Event, Thread
from typing import TYPE_CHECKING, Final

import pytest

from helpers import run_pipx_cli, skip_if_windows
from pipx import paths
from pipx.commands.transaction import VenvBackup, preserve_venv
from pipx.util import PipxError
from pipx.venv import VenvContainer

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


@pytest.mark.usefixtures("pipx_temp_env")
def test_preserve_venv_keeps_the_backup_out_of_the_venv_namespace() -> None:
    venv_dir = paths.ctx.venvs / "demo"
    venv_dir.mkdir(parents=True)
    (venv_dir / "marker").write_text("v1", encoding="utf-8")

    with preserve_venv(venv_dir, enabled=True):
        siblings = {path.name for path in paths.ctx.venvs.iterdir() if path.is_dir()}
        backups = [path for path in paths.ctx.trash.iterdir() if path.is_dir()]

    assert (siblings, len(backups)) == ({"demo"}, 1)


@pytest.mark.usefixtures("pipx_temp_env")
def test_preserve_venv_restores_the_backup_on_failure() -> None:
    venv_dir = paths.ctx.venvs / "demo"
    venv_dir.mkdir(parents=True)
    (venv_dir / "marker").write_text("v1", encoding="utf-8")

    def corrupt_then_fail() -> None:
        (venv_dir / "marker").write_text("v2", encoding="utf-8")
        msg = "boom"
        raise PipxError(msg)

    with pytest.raises(PipxError, match="boom"), preserve_venv(venv_dir, enabled=True):
        corrupt_then_fail()

    assert (venv_dir / "marker").read_text(encoding="utf-8") == "v1"


@pytest.mark.usefixtures("pipx_temp_env")
def test_preserve_venv_without_upfront_copy_restores_a_removed_venv_on_failure() -> None:
    venv_dir = paths.ctx.venvs / "demo"
    venv_dir.mkdir(parents=True)
    (venv_dir / "marker").write_text("v1", encoding="utf-8")

    def rebuild_then_fail(backup: VenvBackup) -> None:
        backup.remove_venv()
        venv_dir.mkdir()
        msg = "boom"
        raise PipxError(msg)

    with pytest.raises(PipxError, match="boom"), preserve_venv(venv_dir, enabled=True, copy_upfront=False) as backup:
        rebuild_then_fail(backup)

    assert (venv_dir / "marker").read_text(encoding="utf-8") == "v1"


@pytest.mark.usefixtures("pipx_temp_env")
def test_preserve_venv_without_upfront_copy_discards_the_removed_venv_on_success() -> None:
    venv_dir = paths.ctx.venvs / "demo"
    venv_dir.mkdir(parents=True)
    (venv_dir / "marker").write_text("v1", encoding="utf-8")

    with preserve_venv(venv_dir, enabled=True, copy_upfront=False) as backup:
        backup.remove_venv()
        venv_dir.mkdir()

    assert (list(venv_dir.iterdir()), [path for path in paths.ctx.trash.iterdir() if path.is_dir()]) == ([], [])


@pytest.mark.parametrize("copy_upfront", [pytest.param(True, id="copied"), pytest.param(False, id="moved")])
@pytest.mark.usefixtures("pipx_temp_env")
def test_preserve_venv_restores_after_another_command_swept_the_trash(copy_upfront: bool) -> None:
    venv_dir: Final[Path] = paths.ctx.venvs / "demo"
    venv_dir.mkdir(parents=True)
    (venv_dir / "marker").write_text("v1", encoding="utf-8")

    def rebuild_while_listing_then_fail(backup: VenvBackup) -> None:
        backup.remove_venv()
        venv_dir.mkdir()
        run_pipx_cli(["environment"])
        msg = "boom"
        raise PipxError(msg)

    with (
        pytest.raises(PipxError, match="boom"),
        _venv_lock_held_elsewhere(venv_dir),
        preserve_venv(venv_dir, enabled=True, copy_upfront=copy_upfront) as backup,
    ):
        rebuild_while_listing_then_fail(backup)

    assert (venv_dir / "marker").read_text(encoding="utf-8") == "v1"


@contextmanager
def _venv_lock_held_elsewhere(venv_dir: Path) -> Generator[None, None, None]:
    # the command owning the backup runs in another process, so the sweep must not find the lock reentrant
    held, release = Event(), Event()

    def hold() -> None:
        with VenvContainer(paths.ctx.venvs).venv_lock(venv_dir):
            held.set()
            release.wait()

    (holder := Thread(target=hold)).start()
    held.wait()
    try:
        yield
    finally:
        release.set()
        holder.join()


@pytest.mark.usefixtures("pipx_temp_env")
def test_setup_sweeps_trash_entries_no_command_holds() -> None:
    paths.ctx.trash.mkdir(parents=True)
    for name in ("demo-abcd1234-pipx-backup", "demo-abcd1234-pipx-reinstall", "pipx-trash.app"):
        (paths.ctx.trash / name).mkdir()
        (paths.ctx.trash / name / "file").touch()
    (paths.ctx.trash / "pipx-trash.app.exe").touch()

    run_pipx_cli(["list"])

    assert list(paths.ctx.trash.glob("*")) == []


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env")
def test_setup_leaves_the_target_of_a_symlinked_trash(tmp_path: Path) -> None:
    (target := tmp_path / "elsewhere").mkdir()
    (target / "file").touch()
    paths.ctx.trash.parent.mkdir(parents=True, exist_ok=True)
    paths.ctx.trash.symlink_to(target)

    run_pipx_cli(["list"])

    assert [path.name for path in target.iterdir()] == ["file"]
