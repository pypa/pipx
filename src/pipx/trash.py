from __future__ import annotations

__lazy_modules__ = ["pipx", "random", "shutil", "string"]

import logging
import random
import shutil
import string
from typing import TYPE_CHECKING, Final

from pipx import paths

if TYPE_CHECKING:
    from pathlib import Path

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def rmdir(path: Path, *, safe_rm: bool = True) -> None:
    if not path.is_dir():
        return

    _LOGGER.info("removing directory %s", path)
    # Windows refuses to delete a running file but lets it be renamed, so pipx moves a directory that survives to the
    # trash for a later run to delete; ignoring errors keeps a locked file from making cleanup fatal
    shutil.rmtree(path, ignore_errors=True)

    if path.is_dir():
        if safe_rm:
            _LOGGER.warning("Failed to delete %s. Will move it to a temp folder to delete later.", path)

            try:
                path.rename(_get_trash_file(path))
            except OSError as error:
                _LOGGER.warning("Failed to move %s to the trash; remove it by hand (%s).", path, error)
        else:
            _LOGGER.warning("Failed to delete %s. You may need to delete it manually.", path)


def _get_trash_file(path: Path) -> Path:
    paths.CTX.trash.mkdir(exist_ok=True)
    prefix: Final[str] = "".join(random.choices(string.ascii_lowercase, k=8))  # ruff:ignore[suspicious-non-cryptographic-random-usage]  # temp filename, not security-sensitive
    return paths.CTX.trash / f"{prefix}.{path.name}"


def rmdir_via_trash(path: Path) -> None:
    # a removal killed halfway leaves the directory whole or gone from its parent, never partly deleted in place
    try:
        path.rename(trash := _get_trash_file(path))
    except OSError:
        rmdir(path)
    else:
        rmdir(trash)


def safe_unlink(file: Path) -> None:
    if not file.is_file() and not file.is_symlink():
        return
    try:
        file.unlink()
    except PermissionError:
        # Windows lets a running file be renamed but not deleted
        file.rename(_get_trash_file(file))


__all__ = [
    "rmdir",
    "rmdir_via_trash",
    "safe_unlink",
]
