from __future__ import annotations

import importlib
import signal
import time
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from threading import Event, Thread
from typing import TYPE_CHECKING, Final

import pytest

from helpers import SKIP_IF_WINDOWS, run_pipx_cli, write_import_probe
from package_info import PKG
from pipx import paths, util
from pipx.commands import transaction
from pipx.commands.transaction import VenvBackup, preserve_venv
from pipx.pipx_metadata_file import PipxMetadata
from pipx.util import PipxError
from pipx.venv import VenvContainer

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from pytest_mock import MockerFixture


def test_preserve_venv_keeps_the_backup_out_of_the_venv_namespace(venv_dir: Path) -> None:
    with preserve_venv(venv_dir, enabled=True):
        siblings: Final[set[str]] = {path.name for path in paths.CTX.venvs.iterdir() if path.is_dir()}
        backups: Final[list[Path]] = [path for path in paths.CTX.trash.iterdir() if path.is_dir()]

    assert (siblings, len(backups)) == ({"demo"}, 1)


@pytest.fixture
def venv_dir(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # requested for its isolated pipx home
) -> Path:
    venv_dir: Final[Path] = paths.CTX.venvs / "demo"
    venv_dir.mkdir(parents=True)
    (venv_dir / "marker").write_text("v1", encoding="utf-8")
    return venv_dir


def test_preserve_venv_restores_the_backup_on_failure(venv_dir: Path) -> None:
    with pytest.raises(PipxError, match="boom"), preserve_venv(venv_dir, enabled=True):
        _corrupt_then_fail(venv_dir)

    assert (venv_dir / "marker").read_text(encoding="utf-8") == "v1"


def _corrupt_then_fail(venv_dir: Path) -> None:
    (venv_dir / "marker").write_text("v2", encoding="utf-8")
    msg = "boom"
    raise PipxError(msg)


def test_preserve_venv_without_upfront_copy_restores_a_removed_venv_on_failure(venv_dir: Path) -> None:
    def rebuild_then_fail(backup: VenvBackup) -> None:
        backup.remove_venv()
        venv_dir.mkdir()
        msg = "boom"
        raise PipxError(msg)

    with pytest.raises(PipxError, match="boom"), preserve_venv(venv_dir, enabled=True, copy_upfront=False) as backup:
        rebuild_then_fail(backup)

    assert (venv_dir / "marker").read_text(encoding="utf-8") == "v1"


def test_preserve_venv_without_upfront_copy_discards_the_removed_venv_on_success(venv_dir: Path) -> None:
    with preserve_venv(venv_dir, enabled=True, copy_upfront=False) as backup:
        backup.remove_venv()
        venv_dir.mkdir()

    assert (list(venv_dir.iterdir()), [path for path in paths.CTX.trash.iterdir() if path.is_dir()]) == ([], [])


@pytest.mark.usefixtures("signal_handlers")
def test_preserve_venv_finishes_the_restore_through_an_interrupt(venv_dir: Path, mocker: MockerFixture) -> None:
    mocker.patch.object(transaction, "rmdir", autospec=True, side_effect=_rmdir_then_interrupt)

    with pytest.raises(KeyboardInterrupt), preserve_venv(venv_dir, enabled=True):
        _corrupt_then_fail(venv_dir)

    assert (venv_dir / "marker").read_text(encoding="utf-8") == "v1"


def _rmdir_then_interrupt(path: Path, *, safe_rm: bool = True) -> None:
    util.rmdir(path, safe_rm=safe_rm)
    signal.raise_signal(signal.SIGINT)


def test_remove_venv_keeps_the_venv_when_the_rename_keeps_failing(venv_dir: Path, mocker: MockerFixture) -> None:
    mocker.patch.object(time, "sleep", autospec=True)
    mocker.patch.object(Path, "rename", autospec=True, side_effect=PermissionError(32, "in use"))

    with (
        pytest.raises(PermissionError, match="in use"),
        preserve_venv(venv_dir, enabled=True, copy_upfront=False) as backup,
    ):
        backup.remove_venv()

    assert (venv_dir / "marker").read_text(encoding="utf-8") == "v1"


def test_remove_venv_moves_the_venv_once_the_rename_succeeds_on_retry(venv_dir: Path, mocker: MockerFixture) -> None:
    mocker.patch.object(time, "sleep", autospec=True)
    real_rename: Final = Path.rename
    attempts: Final[list[Path]] = []

    def rename_after_one_refusal(source: Path, target: Path) -> Path:
        attempts.append(source)
        if len(attempts) == 1:
            raise PermissionError(32, "in use")
        return real_rename(source, target)

    mocker.patch.object(Path, "rename", autospec=True, side_effect=rename_after_one_refusal)

    with preserve_venv(venv_dir, enabled=True, copy_upfront=False) as backup:
        backup.remove_venv()
        moved: Final[list[str]] = [(path / "marker").read_text(encoding="utf-8") for path in paths.CTX.trash.iterdir()]

    assert (venv_dir.exists(), moved, attempts) == (False, ["v1"], [venv_dir, venv_dir])


@pytest.mark.usefixtures("signal_handlers")
def test_remove_venv_restores_a_venv_moved_just_before_an_interrupt(venv_dir: Path, mocker: MockerFixture) -> None:
    real_rename: Final = Path.rename

    def rename_then_interrupt(source: Path, target: Path) -> Path:
        moved: Final[Path] = real_rename(source, target)
        if source == venv_dir:
            signal.raise_signal(signal.SIGINT)
        return moved

    mocker.patch.object(Path, "rename", autospec=True, side_effect=rename_then_interrupt)

    with pytest.raises(KeyboardInterrupt), preserve_venv(venv_dir, enabled=True, copy_upfront=False) as backup:
        backup.remove_venv()

    assert (venv_dir / "marker").read_text(encoding="utf-8") == "v1"


@pytest.mark.parametrize("copy_upfront", [pytest.param(True, id="copied"), pytest.param(False, id="moved")])
def test_preserve_venv_restores_after_another_command_swept_the_trash(venv_dir: Path, copy_upfront: bool) -> None:
    def rebuild_while_listing_then_fail(backup: VenvBackup) -> None:
        backup.remove_venv()
        venv_dir.mkdir()
        run_pipx_cli(["environment"])
        msg = "boom"
        raise PipxError(msg)

    with (
        pytest.raises(PipxError, match="boom"),
        _venv_lock_held_elsewhere(venv_dir),
        preserve_venv(venv_dir, enabled=True, copy_upfront=copy_upfront) as backup,
    ):
        rebuild_while_listing_then_fail(backup)

    assert (venv_dir / "marker").read_text(encoding="utf-8") == "v1"


@contextmanager
def _venv_lock_held_elsewhere(venv_dir: Path) -> Generator[None]:
    # the command owning the backup runs in another process, so the sweep must not find the lock reentrant
    held, release = Event(), Event()

    def hold() -> None:
        with VenvContainer(paths.CTX.venvs).venv_lock(venv_dir):
            held.set()
            release.wait()

    (holder := Thread(target=hold)).start()
    held.wait()
    try:
        yield
    finally:
        release.set()
        holder.join()


@pytest.mark.usefixtures("pipx_temp_env")
def test_setup_sweeps_trash_entries_no_command_holds() -> None:
    paths.CTX.trash.mkdir(parents=True)
    for name in ("demo-abcd1234-pipx-backup", "demo-abcd1234-pipx-reinstall", "pipx-trash.app"):
        (paths.CTX.trash / name).mkdir()
        (paths.CTX.trash / name / "file").touch()
    (paths.CTX.trash / "pipx-trash.app.exe").touch()

    run_pipx_cli(["list"])

    assert list(paths.CTX.trash.glob("*")) == []


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_setup_leaves_the_target_of_a_symlinked_trash(tmp_path: Path) -> None:
    (target := tmp_path / "elsewhere").mkdir()
    (target / "file").touch()
    paths.CTX.trash.parent.mkdir(parents=True, exist_ok=True)
    paths.CTX.trash.symlink_to(target)

    run_pipx_cli(["list"])

    assert [path.name for path in target.iterdir()] == ["file"]


@pytest.mark.parametrize(
    ("package", "command"),
    [
        pytest.param("pycowsay", ["upgrade", "pycowsay"], id="upgrade"),
        pytest.param(PKG["black"]["spec"], ["upgrade-all"], id="upgrade-all"),
        pytest.param("pycowsay", ["install", "--force", "pycowsay"], id="install-force"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_self_change_imports_submodules_of_the_running_version(
    run_from_venv: Callable[[Path], None], package: str, command: list[str]
) -> None:
    assert not run_pipx_cli(["install", package])
    venv_dir: Final[Path] = paths.CTX.venvs / package.partition("==")[0]
    run_from_venv(venv_dir)

    assert not run_pipx_cli(command)
    write_import_probe(venv_dir, "new")

    assert importlib.import_module("running_probe.late").VALUE == "old"


@pytest.mark.usefixtures("pipx_temp_env")
def test_self_upgrade_failure_imports_from_the_restored_venv(
    run_from_venv: Callable[[Path], None], tmp_path: Path
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    venv_dir: Final[Path] = paths.CTX.venvs / "pycowsay"
    run_from_venv(venv_dir)
    metadata: Final[PipxMetadata] = PipxMetadata(venv_dir)
    metadata.main_package = replace(metadata.main_package, package_or_url=str(tmp_path / "missing"))
    metadata.write()

    assert run_pipx_cli(["upgrade", "pycowsay"])

    assert importlib.import_module("running_probe.late").VALUE == "old"
