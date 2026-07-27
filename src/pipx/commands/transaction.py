from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from shutil import Error, copytree
from tempfile import mkdtemp
from typing import TYPE_CHECKING, Final

from pipx import paths
from pipx.util import PipxError, rmdir

if TYPE_CHECKING:
    from collections.abc import Iterator


@contextmanager
def preserve_venv(venv_dir: Path, *, enabled: bool) -> Iterator[None]:
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


__all__ = [
    "preserve_venv",
]
