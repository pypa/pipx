from __future__ import annotations

__lazy_modules__ = ["pipx.trash"]

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from pipx.result import OperationData, OperationResult, OutputMessage
from pipx.trash import rmdir

if TYPE_CHECKING:
    from pipx.venv import VenvContainer


def print_cache_dir(venv_container: VenvContainer) -> OperationResult[CacheData]:
    """Report the directory that holds the cached environments.

    :param venv_container: the container of the cached environments.
    :returns: the result with the directory as its only message.
    """
    directory: Final[str] = str(venv_container)
    return OperationResult(
        command=("cache", "dir"),
        data=CacheData(directory=directory, removed=()),
        messages=(OutputMessage(text=directory),),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class CacheData(OperationData):
    """Result data of the cache commands.

    :ivar directory: the directory of the cache.
    :ivar removed: the names of the cached environments that were removed.
    """

    directory: str
    removed: tuple[str, ...]


def purge_cache(venv_container: VenvContainer) -> OperationResult[CacheData]:
    """Remove every cached environment, each while holding its lock.

    :param venv_container: the container of the cached environments.
    :returns: the result listing the removed environments.
    """
    removed: Final[list[str]] = []
    for venv_dir in venv_container.iter_locked_venv_dirs(tuple(venv_container.iter_venv_dirs())):
        rmdir(venv_dir)
        removed.append(venv_dir.name)
    noun: Final[str] = "environment" if len(removed) == 1 else "environments"
    return OperationResult(
        command=("cache", "purge"),
        data=CacheData(directory=str(venv_container), removed=tuple(removed)),
        messages=(OutputMessage(text=f"Removed {len(removed)} cached {noun}."),),
    )


__all__ = [
    "CacheData",
    "print_cache_dir",
    "purge_cache",
]
