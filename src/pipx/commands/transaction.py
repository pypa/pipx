from __future__ import annotations

__lazy_modules__ = ["pathlib", "pipx", "pipx.fanout", "pipx.util", "shutil", "tempfile"]

from contextlib import contextmanager
from pathlib import Path
from shutil import Error, copytree
from tempfile import mkdtemp
from typing import TYPE_CHECKING, Final

from pipx import paths
from pipx.fanout import finished_on_interrupt
from pipx.util import PipxError, rmdir

if TYPE_CHECKING:
    from collections.abc import Generator

_UNFINISHED_MARKER: Final[str] = "pipx_unfinished"


@contextmanager
def preserve_venv(venv_dir: Path, *, enabled: bool, copy_upfront: bool = True) -> Generator[VenvBackup, None, None]:
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
            mkdtemp(prefix=f"{self._venv_dir.name}-", suffix="-pipx-backup", dir=paths.ctx.trash)
        )
        backup_dir.rmdir()
        return backup_dir

    def remove_venv(self) -> None:
        if self._enabled and self._backup_dir is None:
            # a rename costs the same for any environment size, so rebuilds back up only when they delete
            self._backup_dir = self._new_backup_dir()
            self._venv_dir.rename(self._backup_dir)
        else:
            rmdir(self._venv_dir)

    def restore(self) -> None:
        if self._backup_dir is not None:
            rmdir(self._venv_dir)
            self._backup_dir.rename(self._venv_dir)

    def discard(self) -> None:
        if self._backup_dir is not None:
            rmdir(self._backup_dir)


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


__all__ = [
    "VenvBackup",
    "is_unfinished",
    "marked_unfinished",
    "preserve_venv",
]
