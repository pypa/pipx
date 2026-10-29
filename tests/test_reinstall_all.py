from __future__ import annotations

import datetime as dt
import importlib
import json
import os
import re
import signal
import sys
import threading
import time
from contextlib import suppress
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Final, NoReturn

import pytest

from helpers import PIPX_METADATA_LEGACY_VERSIONS, mock_legacy_venv, run_pipx_cli, skip_if_windows
from package_info import PKG
from pipx import constants, paths, shared_libs
from pipx.pipx_metadata_file import PipxMetadata
from pipx.util import PipxError
from pipx.venv import Venv

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_mock import MockerFixture


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all() -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["reinstall-all", "--python", sys.executable])


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_keeps_injected_pin() -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only"])

    assert not run_pipx_cli(["reinstall-all", "--python", sys.executable])

    assert PipxMetadata(paths.ctx.venvs / "pycowsay").injected_packages["black"].pinned


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_none(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["reinstall-all"])
    captured = capsys.readouterr()
    assert "No packages reinstalled after running 'pipx reinstall-all'" in captured.out


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_legacy_venv(metadata_version: str | None) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)

    assert not run_pipx_cli(["reinstall-all", "--python", sys.executable])


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_suffix() -> None:
    suffix = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])

    assert not run_pipx_cli(["reinstall-all", "--python", sys.executable])


@pytest.mark.parametrize("metadata_version", ["0.1"])
@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_suffix_legacy_venv(metadata_version: str) -> None:
    suffix = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])
    mock_legacy_venv(f"pycowsay{suffix}", metadata_version=metadata_version)

    assert not run_pipx_cli(["reinstall-all", "--python", sys.executable])


@pytest.mark.parametrize(
    ("age_sec", "refreshed"),
    [
        pytest.param(dt.timedelta(days=1).total_seconds(), False, id="recent"),
        pytest.param(shared_libs.SHARED_LIBS_MAX_AGE_SEC + 60, True, id="stale"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_refreshes_shared_pip_only_when_stale(
    age_shared_pip: Callable[[float], float], age_sec: float, refreshed: bool
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    last_upgrade: Final[float] = age_shared_pip(age_sec)

    assert not run_pipx_cli(["reinstall-all"])

    assert (shared_libs.shared_libs.pip_path.stat().st_mtime != last_upgrade) is refreshed


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_restores_package_after_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    reinstall_module = importlib.import_module("pipx.commands.reinstall")

    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    venv_dir = paths.ctx.venvs / "pycowsay"
    metadata_before = (venv_dir / "pipx_metadata.json").read_text()

    def interrupting_install(replacement_venv_dir: Path, *args: object, **kwargs: object) -> NoReturn:
        del args, kwargs
        assert not venv_dir.exists()
        replacement_venv_dir.mkdir()
        (replacement_venv_dir / "partial-install").write_text("new")
        raise KeyboardInterrupt

    monkeypatch.setattr(reinstall_module, "install", interrupting_install)

    assert run_pipx_cli(["reinstall-all", "--python", sys.executable])
    captured = capsys.readouterr()

    assert "Interrupted; restored pycowsay." in captured.err
    assert venv_dir.exists()
    assert (venv_dir / "pipx_metadata.json").read_text() == metadata_before
    assert not (venv_dir / "partial-install").exists()
    assert not any(path.name.endswith("-pipx-reinstall") for path in paths.ctx.venvs.iterdir())


@pytest.fixture
def venv_names(capsys: pytest.CaptureFixture[str]) -> list[str]:
    for spec in ("pycowsay", PKG["pbr"]["spec"], PKG["black"]["spec"]):
        assert not run_pipx_cli(["install", spec])
    capsys.readouterr()
    return [venv_dir.name for venv_dir in paths.ctx.venvs.iterdir() if venv_dir.is_dir()]


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_prints_progress_in_venv_order(
    capsys: pytest.CaptureFixture[str],
    before_venv_subprocess: Callable[[Path, Callable[[], None]], None],
    venv_names: list[str],
) -> None:
    before_venv_subprocess(paths.ctx.venvs / venv_names[0], lambda: time.sleep(0.3))

    assert not run_pipx_cli(["reinstall-all"])

    assert re.findall(r"^installing ([\w-]+)", capsys.readouterr().err, re.MULTILINE) == venv_names


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_reinstalls_the_rest_after_a_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], venv_names: list[str]
) -> None:
    metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / venv_names[0])
    metadata.main_package = replace(metadata.main_package, package_or_url=str(tmp_path / "missing"))
    metadata.write()

    exit_code: Final[int] = run_pipx_cli(["reinstall-all", "--output", "json"])

    result: Final = json.loads(capsys.readouterr().out)
    assert (
        exit_code,
        [environment["environment"] for environment in result["data"]["environments"]],
        [error["environment"] for error in result["errors"]],
    ) == (1, venv_names[1:], venv_names[:1])


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_refreshes_stale_shared_pip_once(
    capsys: pytest.CaptureFixture[str], age_shared_pip: Callable[[float], float], venv_names: list[str]
) -> None:
    del venv_names
    age_shared_pip(shared_libs.SHARED_LIBS_MAX_AGE_SEC + 60)

    assert not run_pipx_cli(["reinstall-all"])

    assert capsys.readouterr().err.count("upgrading shared libraries") == 1


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_restores_interrupted_venv_among_several(
    before_venv_subprocess: Callable[[Path, Callable[[], None]], None], venv_names: list[str]
) -> None:
    interrupted: Final[Path] = paths.ctx.venvs / venv_names[0]
    metadata_before: Final[str] = (interrupted / "pipx_metadata.json").read_text()

    def interrupt() -> NoReturn:
        raise KeyboardInterrupt

    before_venv_subprocess(interrupted, interrupt)

    assert (run_pipx_cli(["reinstall-all"]), (interrupted / "pipx_metadata.json").read_text()) == (1, metadata_before)


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_reports_interrupted_venv_without_traceback(
    capsys: pytest.CaptureFixture[str],
    before_venv_subprocess: Callable[[Path, Callable[[], None]], None],
    venv_names: list[str],
) -> None:
    def interrupt() -> NoReturn:
        raise KeyboardInterrupt

    before_venv_subprocess(paths.ctx.venvs / venv_names[0], interrupt)

    run_pipx_cli(["reinstall-all"])

    err: Final[str] = capsys.readouterr().err
    assert (f"Interrupted; restored {venv_names[0]}." in err, "Traceback" in err) == (True, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_retries_venv_briefly_held_open(mocker: MockerFixture) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    rename: Final = Path.rename
    held: Final[list[Path]] = [paths.ctx.venvs / "pycowsay"]

    def rename_once_released(source: Path, target: Path) -> Path:
        if source in held:
            held.remove(source)
            raise PermissionError(source)
        return rename(source, target)

    mocker.patch.object(Path, "rename", autospec=True, side_effect=rename_once_released)

    assert not run_pipx_cli(["reinstall-all"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_reinstall_all_keeps_shared_man_page_with_its_owner(
    before_venv_subprocess: Callable[[Path, Callable[[], None]], None],
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["install", "pycowsay", "--suffix=_x"])
    before_venv_subprocess(owner := paths.ctx.venvs / "pycowsay", lambda: time.sleep(0.5))

    assert not run_pipx_cli(["reinstall-all"])

    assert (paths.ctx.man_dir / "man6" / "pycowsay.6").resolve().is_relative_to(owner)


@pytest.fixture
def shared_man_page_venvs(pipx_temp_env: None) -> tuple[Path, Path]:  # ruff:ignore[unused-function-argument]  # it sets the pipx home
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["install", "pycowsay", "--suffix=_x"])
    earlier, owner = (venv_dir.resolve() for venv_dir in paths.ctx.venvs.iterdir() if venv_dir.is_dir())
    (paths.ctx.man_dir / "man6" / "pycowsay.6").unlink()
    (paths.ctx.man_dir / "man6" / "pycowsay.6").symlink_to(owner / "share" / "man" / "man6" / "pycowsay.6")
    return earlier, owner


@pytest.fixture
def fail_owner_rebuild_after_takeover(
    shared_man_page_venvs: tuple[Path, Path], mocker: MockerFixture
) -> Callable[[Callable[[], None], Exception], None]:
    earlier, owner = shared_man_page_venvs
    man_page: Final[Path] = paths.ctx.man_dir / "man6" / "pycowsay.6"
    symlink_to: Final = Path.symlink_to
    check_upgrade_shared_libs: Final = Venv.check_upgrade_shared_libs

    def arm(meanwhile: Callable[[], None], failure: Exception) -> None:
        taken_over: Final[threading.Event] = threading.Event()

        def link_and_signal(path: Path, target: Path, target_is_directory: bool = False) -> None:
            symlink_to(path, target, target_is_directory)
            if path == man_page and Path(target).resolve().is_relative_to(earlier):
                taken_over.set()

        def fail_once_taken_over(venv: Venv, *, verbose: bool, pip_args: list[str]) -> None:
            # until the rebuild creates the owner's venv again, its man page dangles and the earlier task takes it
            if venv.root.name != owner.name or venv.root.exists():
                check_upgrade_shared_libs(venv, verbose=verbose, pip_args=pip_args)
                return
            assert taken_over.wait(timeout=60)
            meanwhile()
            raise failure

        mocker.patch.object(Path, "symlink_to", autospec=True, side_effect=link_and_signal)
        mocker.patch.object(Venv, "check_upgrade_shared_libs", autospec=True, side_effect=fail_once_taken_over)

    return arm


@skip_if_windows
@pytest.mark.parametrize(
    "failure",
    [pytest.param(PipxError("rebuild failed"), id="pipx-error"), pytest.param(OSError("disk full"), id="unexpected")],
)
def test_reinstall_all_failed_rebuild_gets_back_shared_man_page(
    shared_man_page_venvs: tuple[Path, Path],
    fail_owner_rebuild_after_takeover: Callable[[Callable[[], None], Exception], None],
    failure: Exception,
) -> None:
    fail_owner_rebuild_after_takeover(lambda: None, failure)

    with suppress(OSError):
        run_pipx_cli(["reinstall-all"])

    assert (paths.ctx.man_dir / "man6" / "pycowsay.6").resolve().is_relative_to(shared_man_page_venvs[1])


@skip_if_windows
def test_reinstall_all_failed_rebuild_keeps_man_page_replaced_elsewhere(
    fail_owner_rebuild_after_takeover: Callable[[Callable[[], None], Exception], None], tmp_path: Path
) -> None:
    man_page: Final[Path] = paths.ctx.man_dir / "man6" / "pycowsay.6"
    (elsewhere := tmp_path / "pycowsay.6").touch()

    def replace_link() -> None:
        man_page.unlink()
        man_page.symlink_to(elsewhere)

    fail_owner_rebuild_after_takeover(replace_link, PipxError("rebuild failed"))

    assert run_pipx_cli(["reinstall-all"])

    assert man_page.resolve() == elsewhere.resolve()


@skip_if_windows
def test_reinstall_all_failed_rebuild_keeps_shared_man_page_nobody_took(
    shared_man_page_venvs: tuple[Path, Path], before_venv_subprocess: Callable[[Path, Callable[[], None]], None]
) -> None:
    def fail() -> NoReturn:
        msg = "rebuild failed"
        raise PipxError(msg)

    before_venv_subprocess(shared_man_page_venvs[1] / "bin", fail)

    assert run_pipx_cli(["reinstall-all"])

    assert (paths.ctx.man_dir / "man6" / "pycowsay.6").resolve().is_relative_to(shared_man_page_venvs[1])


@pytest.mark.skipif(constants.WINDOWS, reason="os.kill with SIGINT terminates the process on Windows")
@pytest.mark.usefixtures("pipx_temp_env", "signal_handlers")
def test_reinstall_all_restores_running_venvs_on_sigint_to_pipx_alone(
    before_venv_subprocess: Callable[[Path, Callable[[], None]], None], venv_names: list[str]
) -> None:
    venv_dirs: Final[list[Path]] = [paths.ctx.venvs / name for name in venv_names]
    for venv_dir in venv_dirs:
        (venv_dir / "marker").touch()

    def interrupt() -> None:
        # signals this process only, as kill -INT <pid> does, so the running pip and venv children carry on
        os.kill(os.getpid(), signal.SIGINT)

    def hold() -> None:
        # until pipx has acted on the signal and restored the first venv, or another one could finish first and rightly
        # keep its new venv
        deadline: Final[float] = time.monotonic() + 5
        while not (venv_dirs[0] / "marker").exists() and time.monotonic() < deadline:
            time.sleep(0.01)

    before_venv_subprocess(venv_dirs[0], interrupt)
    for venv_dir in venv_dirs[1:]:
        before_venv_subprocess(venv_dir, hold)

    exit_code: Final[int] = run_pipx_cli(["reinstall-all"])

    assert (exit_code, [(venv_dir / "marker").exists() for venv_dir in venv_dirs]) == (1, [True] * len(venv_dirs))
