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
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Final, NoReturn

import pytest

from helpers import PIPX_METADATA_LEGACY_VERSIONS, mock_legacy_venv, run_pipx_cli, set_shared_pip_age
from package_info import PKG
from pipx import constants, paths, shared_libs
from pipx.pipx_metadata_file import PipxMetadata

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

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
def test_reinstall_all_refreshes_shared_pip_only_when_stale(age_sec: float, refreshed: bool) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    last_upgrade: Final[float] = set_shared_pip_age(age_sec)

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

    assert "Reinstall failed; restored pycowsay." in captured.err
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
    capsys: pytest.CaptureFixture[str], venv_names: list[str]
) -> None:
    del venv_names
    set_shared_pip_age(shared_libs.SHARED_LIBS_MAX_AGE_SEC + 60)

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
def test_reinstall_all_gives_shared_man_page_to_the_last_venv(
    before_venv_subprocess: Callable[[Path, Callable[[], None]], None],
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["install", "pycowsay", "--suffix=_x"])
    first, last = (venv_dir for venv_dir in paths.ctx.venvs.iterdir() if venv_dir.is_dir())
    before_venv_subprocess(first, lambda: time.sleep(0.5))

    assert not run_pipx_cli(["reinstall-all"])

    assert (paths.ctx.man_dir / "man6" / "pycowsay.6").resolve().is_relative_to(last)


@pytest.fixture
def default_sigint_handler() -> Iterator[None]:
    previous: Final = signal.signal(signal.SIGINT, signal.default_int_handler)
    yield
    signal.signal(signal.SIGINT, previous)


@pytest.mark.skipif(constants.WINDOWS, reason="os.kill with SIGINT terminates the process on Windows")
@pytest.mark.usefixtures("pipx_temp_env", "default_sigint_handler")
def test_reinstall_all_restores_running_venvs_on_sigint_to_pipx_alone(
    before_venv_subprocess: Callable[[Path, Callable[[], None]], None], venv_names: list[str]
) -> None:
    venv_dirs: Final[list[Path]] = [paths.ctx.venvs / name for name in venv_names]
    for venv_dir in venv_dirs:
        (venv_dir / "marker").touch()
    interrupted: Final[threading.Event] = threading.Event()

    def interrupt() -> None:
        # signals this process only, as kill -INT <pid> does, so the running pip and venv children carry on
        os.kill(os.getpid(), signal.SIGINT)
        interrupted.set()

    def hold() -> None:
        interrupted.wait(timeout=5)

    before_venv_subprocess(venv_dirs[0], interrupt)
    # the other venvs stay mid-reinstall until the signal, or one could finish first and rightly keep its new venv
    for venv_dir in venv_dirs[1:]:
        before_venv_subprocess(venv_dir, hold)

    exit_code: Final[int] = run_pipx_cli(["reinstall-all"])

    assert (exit_code, [(venv_dir / "marker").exists() for venv_dir in venv_dirs]) == (1, [True] * len(venv_dirs))
