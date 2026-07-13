from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from shutil import Error, copytree
from tempfile import mkdtemp
from typing import Final

from pipx.util import PipxError, rmdir


@contextmanager
def preserve_venv(venv_dir: Path, *, enabled: bool) -> Iterator[None]:
    if not enabled:
        yield
        return

    backup_dir: Final[Path] = Path(mkdtemp(prefix=f".{venv_dir.name}-", suffix="-pipx-backup", dir=venv_dir.parent))
    backup_dir.rmdir()
    try:
        copytree(venv_dir, backup_dir, symlinks=True)
    except (Error, OSError) as error:
        rmdir(backup_dir)
        raise PipxError(f"pipx could not back up environment {venv_dir.name}: {error}") from error

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
