from __future__ import annotations

__lazy_modules__ = [
    "contextlib",
    "pipx.commands.common",
    "pipx.commands.uninstall",
    "pipx.paths",
    "pipx.trash",
    "pipx.venv",
]

from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from pipx.commands.common import get_venv_package_infos, get_venv_resource_paths
from pipx.commands.uninstall import UninstallData, uninstall_all
from pipx.constants import COMPLETION_SECTIONS, MAN_SECTIONS
from pipx.paths import CTX
from pipx.result import OperationData, OperationResult, OutputMessage, OutputStream
from pipx.trash import rmdir
from pipx.venv import Venv

if TYPE_CHECKING:
    from pathlib import Path

    from pipx.venv import VenvContainer


def reset(
    venv_container: VenvContainer,
    local_bin_dir: Path,
    local_man_dir: Path,
    *,
    verbose: bool,
    dry_run: bool,
) -> OperationResult[ResetData]:
    """Remove every environment, exposed resource and cached file that pipx manages.

    :param venv_container: the container of the environments.
    :param local_bin_dir: the directory the apps are exposed in.
    :param local_man_dir: the directory the man pages are exposed in.
    :param verbose: show the progress of the reset.
    :param dry_run: list what would be removed without removing it.
    :returns: the result listing the packages and the paths removed.
    """
    targets: Final[tuple[Path, ...]] = tuple(
        target
        for target in (
            CTX.venvs,
            CTX.shared_libs,
            CTX.venv_cache,
            CTX.standalone_python_cachedir,
            CTX.logs,
            CTX.trash,
        )
        if target.is_dir()
    )
    if dry_run:
        # the exposed apps, manual pages, and completions live outside the pipx home, so list them too or the dry run
        # understates what a real reset unlinks
        would_remove: Final[tuple[Path, ...]] = (
            *_exposed_resource_paths(venv_container, local_bin_dir, local_man_dir),
            *targets,
        )
        return OperationResult(
            command=("reset",),
            data=ResetData(
                packages=tuple(sorted(venv_dir.name for venv_dir in venv_container.iter_venv_dirs())),
                removed=tuple(str(path) for path in would_remove),
            ),
            messages=tuple(
                OutputMessage(text=f"Would remove {path}", stream=OutputStream.STDOUT) for path in would_remove
            ),
        )

    # uninstalling unlinks the apps and the man pages, which live outside the pipx home
    uninstalled: Final[OperationResult[UninstallData]] = uninstall_all(
        venv_container, local_bin_dir, local_man_dir, verbose=verbose
    )
    removed: Final[tuple[str, ...]] = tuple(str(target) for target in targets if _remove(target))
    return OperationResult(
        command=("reset",),
        data=ResetData(
            packages=tuple(package.environment for package in uninstalled.data.packages),
            removed=removed,
        ),
        messages=(
            *uninstalled.messages,
            OutputMessage(text=f"pipx is back to a fresh install under {CTX.home}.", stream=OutputStream.STDOUT),
        ),
        exit_code=uninstalled.exit_code,
    )


def _exposed_resource_paths(
    venv_container: VenvContainer, local_bin_dir: Path, local_man_dir: Path
) -> tuple[Path, ...]:
    exposed: set[Path] = set()
    for venv_dir in venv_container.iter_venv_dirs():
        venv = Venv(venv_dir)
        package_infos = get_venv_package_infos(venv)
        exposed |= get_venv_resource_paths("app", venv.bin_path, local_bin_dir, package_infos)
        for man_section in MAN_SECTIONS:
            exposed |= get_venv_resource_paths(
                "man", venv.man_path / man_section, local_man_dir / man_section, package_infos
            )
        for completion_section in COMPLETION_SECTIONS:
            exposed |= get_venv_resource_paths(
                "completion",
                venv.man_path.parent / completion_section,
                CTX.completion_dir / completion_section,
                package_infos,
            )
    return tuple(sorted(exposed))


@dataclass(frozen=True, slots=True, kw_only=True)
class ResetData(OperationData):
    """Result data of the reset command.

    :ivar packages: the names of the packages whose environments were reset.
    :ivar removed: the names of the directories that were removed.
    """

    packages: tuple[str, ...]
    removed: tuple[str, ...]


def _remove(target: Path) -> bool:
    if target == CTX.logs:
        # this command logs into one of these files, and Windows refuses to unlink a file it holds open
        for entry in target.iterdir():
            if entry == CTX.log_file:
                continue
            if entry.is_dir():
                rmdir(entry, safe_rm=False)
            else:
                with suppress(OSError):
                    entry.unlink()
        return True
    rmdir(target, safe_rm=False)
    return not target.is_dir()


__all__ = [
    "ResetData",
    "reset",
]
