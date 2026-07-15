from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from pipx.result import OperationData, OperationResult, OutputMessage
from pipx.util import rmdir

if TYPE_CHECKING:
    from pathlib import Path

    from pipx.venv import VenvContainer


@dataclass(frozen=True)
class CacheData(OperationData):
    directory: str
    removed: tuple[str, ...]


def print_cache_dir(venv_container: VenvContainer) -> OperationResult[CacheData]:
    directory: Final[str] = str(venv_container)
    return OperationResult(
        command=("cache", "dir"),
        data=CacheData(directory=directory, removed=()),
        messages=(OutputMessage(directory),),
    )


def purge_cache(venv_container: VenvContainer) -> OperationResult[CacheData]:
    venv_dirs: Final[tuple[Path, ...]] = tuple(venv_container.iter_venv_dirs())
    removed: Final[list[str]] = []
    for venv_dir in venv_container.iter_locked_venv_dirs(venv_dirs):
        rmdir(venv_dir)
        removed.append(venv_dir.name)
    noun: Final[str] = "environment" if len(removed) == 1 else "environments"
    return OperationResult(
        command=("cache", "purge"),
        data=CacheData(directory=str(venv_container), removed=tuple(removed)),
        messages=(OutputMessage(f"Removed {len(removed)} cached {noun}."),),
    )


__all__ = [
    "CacheData",
    "print_cache_dir",
    "purge_cache",
]
