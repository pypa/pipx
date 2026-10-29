from __future__ import annotations

__lazy_modules__ = ["pathlib", "pipx", "pipx.fanout", "pipx.trash", "pipx.util", "pipx.venv", "shutil", "tempfile"]

import sys
import time
from contextlib import contextmanager, suppress
from pathlib import Path
from shutil import Error, copytree
from tempfile import mkdtemp
from typing import TYPE_CHECKING, Final

from pipx import paths
from pipx.fanout import finished_on_interrupt, uninterrupted
from pipx.trash import rmdir
from pipx.util import PipxError
from pipx.venv import VenvContainer

if TYPE_CHECKING:
    from collections.abc import Generator

    from filelock import BaseFileLock

_UNFINISHED_MARKER: Final[str] = "pipx_unfinished"
_IN_USE_LOCK: Final[str] = "pipx_in_use.lock"
_BACKUP_SUFFIX: Final[str] = "-pipx-backup"
REINSTALL_BACKUP_SUFFIX: Final[str] = "-pipx-reinstall"
# filelock releases a lock it garbage collects, so the locks on copies the running pipx imports from live here
_HELD_COPIES: Final[dict[Path, BaseFileLock]] = {}


@contextmanager
def preserve_venv(venv_dir: Path, *, enabled: bool, copy_upfront: bool = True) -> Generator[VenvBackup]:
    backup: Final[VenvBackup] = VenvBackup(venv_dir, enabled=enabled)
    if enabled and (copy_upfront or runs_from_venv(venv_dir)):
        backup.copy()
    try:
        yield backup
    except (Exception, KeyboardInterrupt):  # any failure, an interrupt included, rolls the environment back
        backup.restore()
        raise
    else:
        backup.discard()


class VenvBackup:
    def __init__(self, venv_dir: Path, *, enabled: bool) -> None:
        self._venv_dir: Final[Path] = venv_dir
        self._enabled: Final[bool] = enabled
        self._backup_dir: Path | None = None
        self._holds_imports: bool = False

    def copy(self) -> None:
        backup_dir: Final[Path] = self._new_backup_dir()
        try:
            copytree(self._venv_dir, backup_dir, symlinks=True)
        except (Error, OSError) as error:
            rmdir(backup_dir)
            msg: Final[str] = f"pipx could not back up environment {self._venv_dir.name}: {error}"
            raise PipxError(msg) from error
        self._backup_dir = backup_dir
        self._holds_imports = runs_from_venv(self._venv_dir) and import_from_copy(backup_dir)

    def _new_backup_dir(self) -> Path:
        # the backup lives in the trash, not beside the venv, so a concurrent list or reinstall-all does not enumerate
        # it as a broken environment; the trash shares the home's filesystem, so restoring it is an atomic rename
        paths.CTX.trash.mkdir(parents=True, exist_ok=True)
        backup_dir: Final[Path] = Path(
            mkdtemp(prefix=f"{self._venv_dir.name}-", suffix=_BACKUP_SUFFIX, dir=paths.CTX.trash)
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
                release_copy(self._backup_dir)
                self._backup_dir.rename(self._venv_dir)
                if self._holds_imports:
                    repoint_imports(self._backup_dir, Path(sys.prefix))

    def discard(self) -> None:
        # the running pipx keeps importing from its copy, so the trash cleanup of the next pipx run removes it
        if self._backup_dir is not None and not self._holds_imports:
            rmdir(self._backup_dir)


def runs_from_venv(venv_dir: Path) -> bool:
    return Path(sys.prefix).resolve() == venv_dir.resolve()


def import_from_copy(copy_dir: Path) -> bool:
    if not repoint_imports(Path(sys.prefix), copy_dir):
        return False
    from filelock import FileLock  # ruff:ignore[import-outside-top-level]  # pulls in asyncio, slows startup

    # the running pipx imports from the copy until it exits, long after it releases the venv lock, so it holds a lock
    # of its own that keeps a concurrent trash sweep away; the operating system drops it when the process ends
    (lock := FileLock(copy_dir / _IN_USE_LOCK)).acquire()
    _HELD_COPIES[copy_dir] = lock
    return True


def repoint_imports(source: Path, target: Path) -> bool:
    # pipx changing the venv it runs from puts another version in its place; later imports (lazy ones and those inside
    # functions) must load the old code from its copy, or old and new modules mix; sys.path finds top-level modules and
    # each package's __path__ its submodules
    moved: Final[list[str]] = [_moved(entry, source, target) for entry in sys.path]
    changed: Final[bool] = moved != sys.path
    sys.path[:] = moved
    for module in tuple(sys.modules.values()):
        if isinstance(search_path := getattr(module, "__path__", None), list):
            search_path[:] = [_moved(entry, source, target) for entry in search_path]
    return changed


def _moved(entry: str, source: Path, target: Path) -> str:
    return str(target / path.relative_to(source)) if (path := Path(entry)).is_relative_to(source) else entry


def release_copy(copy_dir: Path) -> None:
    # the copy goes back in place of the venv, which must not carry the lock file
    if (lock := _HELD_COPIES.pop(copy_dir, None)) is not None:
        lock.release()
        (copy_dir / _IN_USE_LOCK).unlink(missing_ok=True)


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
def marked_unfinished(venv_dir: Path) -> Generator[None]:
    # an interrupt, a crash or a kill leaves the mark behind, which tells the next upgrade or reinstall to rebuild the
    # environment; an error pipx reports clears it
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
    # rmdir refuses a symlinked trash, so handing one to it never empties the link's target
    if paths.CTX.trash.is_symlink() or not paths.CTX.trash.is_dir():
        rmdir(paths.CTX.trash, safe_rm=False)
        return
    for entry in paths.CTX.trash.iterdir():
        if entry.is_symlink() or not entry.is_dir():
            with suppress(OSError):
                entry.unlink()
        elif not _is_backup_in_use(entry):
            rmdir(entry, safe_rm=False)


def _is_backup_in_use(entry: Path) -> bool:
    # a command keeps its environment's lock for as long as it may restore that environment from its backup, and a
    # pipx that changed its own environment keeps the copy's lock for as long as it imports from it
    suffix: Final[str | None] = next(
        (candidate for candidate in (_BACKUP_SUFFIX, REINSTALL_BACKUP_SUFFIX) if entry.name.endswith(candidate)), None
    )
    if suffix is None:
        return False
    from filelock import FileLock  # ruff:ignore[import-outside-top-level]  # pulls in asyncio, slows startup

    venv_name: Final[str] = entry.name.removesuffix(suffix).rpartition("-")[0]
    if _is_held(VenvContainer(paths.CTX.venvs).venv_lock(paths.CTX.venvs / venv_name)):
        return True
    # only a copy some pipx imported from has the lock file, and acquiring a missing one would create it
    return (in_use := entry / _IN_USE_LOCK).is_file() and _is_held(FileLock(in_use))


def _is_held(lock: BaseFileLock) -> bool:
    from filelock import Timeout  # ruff:ignore[import-outside-top-level]  # pulls in asyncio, slows startup

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
    "import_from_copy",
    "is_unfinished",
    "marked_unfinished",
    "preserve_venv",
    "release_copy",
    "rename_once_released",
    "repoint_imports",
    "runs_from_venv",
]
