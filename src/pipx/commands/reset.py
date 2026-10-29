from __future__ import annotations

__lazy_modules__ = ["contextlib", "pipx", "pipx.commands.common", "pipx.commands.uninstall", "pipx.trash", "pipx.venv"]

from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from pipx import paths
from pipx.commands.common import get_venv_package_infos, get_venv_resource_paths
from pipx.commands.uninstall import UninstallData, uninstall_all
from pipx.constants import COMPLETION_SECTIONS, MAN_SECTIONS
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
    targets: Final[tuple[Path, ...]] = _reset_targets()
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
            OutputMessage(text=f"pipx is back to a fresh install under {paths.CTX.home}.", stream=OutputStream.STDOUT),
        ),
        exit_code=uninstalled.exit_code,
    )


def _reset_targets() -> tuple[Path, ...]:
    return tuple(
        target
        for target in (
            paths.CTX.venvs,
            paths.CTX.shared_libs,
            paths.CTX.venv_cache,
            paths.CTX.standalone_python_cachedir,
            paths.CTX.logs,
            paths.CTX.trash,
        )
        if target.is_dir()
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
                paths.CTX.completion_dir / completion_section,
                package_infos,
            )
    return tuple(sorted(exposed))


@dataclass(frozen=True, slots=True, kw_only=True)
class ResetData(OperationData):
    packages: tuple[str, ...]
    removed: tuple[str, ...]


def _remove(target: Path) -> bool:
    if target == paths.CTX.logs:
        _clear_logs(target)
        return True
    rmdir(target, safe_rm=False)
    return not target.is_dir()


def _clear_logs(logs: Path) -> None:
    # this command logs into one of these files, and Windows refuses to unlink a file it holds open
    for entry in logs.iterdir():
        if entry == paths.CTX.log_file:
            continue
        if entry.is_dir():
            rmdir(entry, safe_rm=False)
        else:
            with suppress(OSError):
                entry.unlink()


__all__ = [
    "ResetData",
    "reset",
]
