from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from pipx import paths
from pipx.commands.uninstall import UninstallData, uninstall_all
from pipx.result import OperationData, OperationResult, OutputMessage, OutputStream
from pipx.util import rmdir

if TYPE_CHECKING:
    from pathlib import Path

    from pipx.venv import VenvContainer


@dataclass(frozen=True)
class ResetData(OperationData):
    packages: tuple[str, ...]
    removed: tuple[str, ...]


def reset(
    venv_container: VenvContainer,
    local_bin_dir: Path,
    local_man_dir: Path,
    verbose: bool,
    *,
    dry_run: bool = False,
) -> OperationResult[ResetData]:
    targets: Final[tuple[Path, ...]] = _reset_targets()
    if dry_run:
        return OperationResult(
            command="reset",
            data=ResetData(
                packages=tuple(sorted(venv_dir.name for venv_dir in venv_container.iter_venv_dirs())),
                removed=tuple(str(target) for target in targets),
            ),
            messages=tuple(OutputMessage(f"Would remove {target}", stream=OutputStream.STDOUT) for target in targets),
        )

    # uninstalling is what unlinks the apps and the man pages, which live outside the pipx home
    uninstalled: Final[OperationResult[UninstallData]] = uninstall_all(
        venv_container, local_bin_dir, local_man_dir, verbose
    )
    removed: Final[tuple[str, ...]] = tuple(str(target) for target in targets if _remove(target))
    return OperationResult(
        command="reset",
        data=ResetData(
            packages=tuple(package.environment for package in uninstalled.data.packages),
            removed=removed,
        ),
        messages=(
            *uninstalled.messages,
            OutputMessage(f"pipx is back to a fresh install under {paths.ctx.home}.", stream=OutputStream.STDOUT),
        ),
        exit_code=uninstalled.exit_code,
    )


def _reset_targets() -> tuple[Path, ...]:
    return tuple(
        target
        for target in (
            paths.ctx.venvs,
            paths.ctx.shared_libs,
            paths.ctx.venv_cache,
            paths.ctx.standalone_python_cachedir,
            paths.ctx.logs,
            paths.ctx.trash,
        )
        if target.is_dir()
    )


def _remove(target: Path) -> bool:
    if target == paths.ctx.logs:
        _clear_logs(target)
        return True
    rmdir(target, safe_rm=False)
    return not target.is_dir()


def _clear_logs(logs: Path) -> None:
    # this very command logs into one of these files, and Windows refuses to unlink a file it holds open
    for entry in logs.iterdir():
        if entry == paths.ctx.log_file:
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
