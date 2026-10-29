from __future__ import annotations

__lazy_modules__ = ["pathlib", "pipx", "pipx.fanout", "pipx.util", "pipx.venv", "shutil", "tempfile"]

import time
from contextlib import contextmanager, suppress
from pathlib import Path
from shutil import Error, copytree
from tempfile import mkdtemp
from typing import TYPE_CHECKING, Final

from pipx import paths
from pipx.fanout import finished_on_interrupt, uninterrupted
from pipx.util import PipxError, rmdir
from pipx.venv import VenvContainer

if TYPE_CHECKING:
    from collections.abc import Generator

    from filelock import BaseFileLock

_UNFINISHED_MARKER: Final[str] = "pipx_unfinished"
_BACKUP_SUFFIX: Final[str] = "-pipx-backup"
REINSTALL_BACKUP_SUFFIX: Final[str] = "-pipx-reinstall"


@contextmanager
def preserve_venv(venv_dir: Path, *, enabled: bool, copy_upfront: bool = True) -> Generator[VenvBackup]:
    backup: Final[VenvBackup] = VenvBackup(venv_dir, enabled=enabled)
    if enabled and copy_upfront:
        backup.copy()
    try:
        yield backup
    except (Exception, KeyboardInterrupt):
        backup.restore()
        raise
    else:
        backup.discard()


class VenvBackup:
    def __init__(self, venv_dir: Path, *, enabled: bool) -> None:
        self._venv_dir: Final[Path] = venv_dir
        self._enabled: Final[bool] = enabled
        self._backup_dir: Path | None = None

    def copy(self) -> None:
        backup_dir: Final[Path] = self._new_backup_dir()
        try:
            copytree(self._venv_dir, backup_dir, symlinks=True)
        except (Error, OSError) as error:
            rmdir(backup_dir)
            msg = f"pipx could not back up environment {self._venv_dir.name}: {error}"
            raise PipxError(msg) from error
        self._backup_dir = backup_dir

    def _new_backup_dir(self) -> Path:
        # the backup lives in the trash, not beside the venv, so a concurrent list or reinstall-all does not enumerate
        # it as a broken environment; the trash shares the home's filesystem, so restoring it is an atomic rename
        paths.ctx.trash.mkdir(parents=True, exist_ok=True)
        backup_dir: Final[Path] = Path(
            mkdtemp(prefix=f"{self._venv_dir.name}-", suffix=_BACKUP_SUFFIX, dir=paths.ctx.trash)
        )
        backup_dir.rmdir()
        return backup_dir

    def remove_venv(self) -> None:
        if self._enabled and self._backup_dir is None:
            # a rename costs the same for any environment size, so rebuilds back up only when they delete
            backup_dir: Final[Path] = self._new_backup_dir()
            # a signal between the rename and recording the backup would leave restore unaware of the moved venv
            with uninterrupted():
                rename_once_released(self._venv_dir, backup_dir)
                self._backup_dir = backup_dir
        else:
            rmdir(self._venv_dir)

    def restore(self) -> None:
        if self._backup_dir is not None:
            # a signal between the two steps would leave the venv deleted and its only copy in the trash
            with uninterrupted():
                rmdir(self._venv_dir)
                self._backup_dir.rename(self._venv_dir)

    def discard(self) -> None:
        if self._backup_dir is not None:
            rmdir(self._backup_dir)


def rename_once_released(source: Path, target: Path) -> None:
    # Windows refuses to rename a directory while a handle inside it is open, and a concurrent rebuild of another venv
    # briefly opens this one's scripts directory while it matches the launcher copies in the bin directory to venvs
    for delay in (0.05, 0.1, 0.2, 0.4, 0.8):
        try:
            source.rename(target)
        except PermissionError:
            time.sleep(delay)
        else:
            return
    source.rename(target)


@contextmanager
def marked_unfinished(venv_dir: Path) -> Generator[None, None, None]:
    """Mark the environment as half changed until the block completes or fails with an error pipx reports.

    An interrupt, a crash or a kill leaves the mark behind, which tells the next upgrade or reinstall to rebuild it.
    """
    with finished_on_interrupt():
        marker: Final[Path] = venv_dir / _UNFINISHED_MARKER
        marker.touch()
        try:
            yield
        except PipxError:
            marker.unlink()
            raise
        marker.unlink()


def is_unfinished(venv_dir: Path) -> bool:
    return (venv_dir / _UNFINISHED_MARKER).is_file()


def empty_trash() -> None:
    # a symlinked trash is left to rmdir, which refuses it, so its target is never emptied
    if paths.ctx.trash.is_symlink() or not paths.ctx.trash.is_dir():
        rmdir(paths.ctx.trash, safe_rm=False)
        return
    for entry in paths.ctx.trash.iterdir():
        if entry.is_symlink() or not entry.is_dir():
            with suppress(OSError):
                entry.unlink()
        elif not _is_backup_in_use(entry):
            rmdir(entry, safe_rm=False)


def _is_backup_in_use(entry: Path) -> bool:
    # a command keeps its environment's lock for as long as it may restore that environment from its backup
    suffix: Final[str | None] = next(
        (candidate for candidate in (_BACKUP_SUFFIX, REINSTALL_BACKUP_SUFFIX) if entry.name.endswith(candidate)), None
    )
    if suffix is None:
        return False
    from filelock import Timeout  # ruff:ignore[import-outside-top-level]  # pulls in asyncio, slows startup

    venv_name: Final[str] = entry.name.removesuffix(suffix).rpartition("-")[0]
    lock: Final[BaseFileLock] = VenvContainer(paths.ctx.venvs).venv_lock(paths.ctx.venvs / venv_name)
    try:
        lock.acquire(timeout=0)
    except (Timeout, OSError):
        return True
    lock.release()
    return False


__all__ = [
    "REINSTALL_BACKUP_SUFFIX",
    "VenvBackup",
    "empty_trash",
    "is_unfinished",
    "marked_unfinished",
    "preserve_venv",
    "rename_once_released",
]
