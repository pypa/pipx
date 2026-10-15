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
def preserve_venv(venv_dir: Path, *, enabled: bool) -> Generator[None, None, None]:
    if not enabled:
        yield
        return

    # the backup lives in the trash, not beside the venv, so a concurrent list or reinstall-all does not enumerate it as
    # a broken environment; the trash shares the home's filesystem, so restoring it is still an atomic rename
    paths.ctx.trash.mkdir(parents=True, exist_ok=True)
    backup_dir: Final[Path] = Path(mkdtemp(prefix=f"{venv_dir.name}-", suffix="-pipx-backup", dir=paths.ctx.trash))
    backup_dir.rmdir()
    try:
        copytree(venv_dir, backup_dir, symlinks=True)
    except (Error, OSError) as error:
        rmdir(backup_dir)
        msg = f"pipx could not back up environment {venv_dir.name}: {error}"
        raise PipxError(msg) from error

    try:
        yield
    except (Exception, KeyboardInterrupt):
        rmdir(venv_dir)
        backup_dir.rename(venv_dir)
        raise
    else:
        rmdir(backup_dir)


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
    "is_unfinished",
    "marked_unfinished",
    "preserve_venv",
]
