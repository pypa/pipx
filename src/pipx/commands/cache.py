from __future__ import annotations

from typing import TYPE_CHECKING, Final

from pipx.constants import EXIT_CODE_OK, ExitCode
from pipx.util import rmdir

if TYPE_CHECKING:
    from pathlib import Path

    from pipx.venv import VenvContainer


def print_cache_dir(venv_container: VenvContainer) -> ExitCode:
    print(venv_container)
    return EXIT_CODE_OK


def purge_cache(venv_container: VenvContainer) -> ExitCode:
    venv_dirs: Final[tuple[Path, ...]] = tuple(venv_container.iter_venv_dirs())
    removed = 0
    for venv_dir in venv_container.iter_locked_venv_dirs(venv_dirs):
        rmdir(venv_dir)
        removed += 1
    noun: Final[str] = "environment" if removed == 1 else "environments"
    print(f"Removed {removed} cached {noun}.")
    return EXIT_CODE_OK


__all__ = [
    "print_cache_dir",
    "purge_cache",
]
