from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import TYPE_CHECKING, Final

import pytest
from filelock import AcquireReturnProxy, FileLock

from helpers import SKIP_IF_WINDOWS, run_pipx_cli
from pipx import paths, shared_libs
from pipx.backends.pip import PipBackend
from pipx.constants import PIPX_SHARED_PTH, WINDOWS
from pipx.subprocess_runner import run_subprocess
from pipx.venv import Venv

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_create_venv_lists_every_shared_site_packages_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # purelib and platlib coincide on the platforms CI runs, so pin a split layout to keep both lines under test
    shared_site_packages: Final[list[Path]] = [tmp_path / "shared" / "purelib", tmp_path / "shared" / "platlib"]
    monkeypatch.setattr(type(shared_libs.SHARED_LIBS), "site_packages", property(lambda _self: shared_site_packages))
    venv_root: Final[Path] = tmp_path / "venv"

    PipBackend().create_venv(
        venv_root, python=sys.executable, venv_args=[], pip_args=[], include_pip=False, verbose=False
    )

    pth_file: Final[Path] = next(venv_root.glob(f"**/{PIPX_SHARED_PTH}"))
    assert pth_file.read_text().splitlines() == [str(path) for path in shared_site_packages]


@pytest.mark.parametrize(
    ("mtime_minus_now", "needs_upgrade"),
    [
        pytest.param(-shared_libs.SHARED_LIBS_MAX_AGE_SEC - 5 * 60, True, id="older-than-max-age"),
        pytest.param(-shared_libs.SHARED_LIBS_MAX_AGE_SEC + 5 * 60, False, id="younger-than-max-age"),
    ],
)
@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_auto_update_shared_libs(mtime_minus_now: float, needs_upgrade: bool) -> None:
    now: Final[float] = time.time()
    shared_libs.SHARED_LIBS.create(verbose=True, pip_args=[])
    shared_libs.SHARED_LIBS.has_been_updated_this_run = False

    os.utime(shared_libs.SHARED_LIBS.pip_path, (now, mtime_minus_now + now))

    assert shared_libs.SHARED_LIBS.needs_upgrade is needs_upgrade


@pytest.mark.skipif(not WINDOWS, reason="Windows-specific test")
@pytest.mark.parametrize(
    ("installed", "expected"),
    [
        pytest.param("pythonw.exe", False, id="missing-interpreter"),
        pytest.param("python.exe", True, id="existing-interpreter"),
    ],
)
@pytest.mark.usefixtures("shared_pip_layout")
def test_shared_libs_validity_checks_base_interpreter(tmp_path: Path, installed: str, expected: bool) -> None:
    (home := tmp_path / "base-python").mkdir()
    (home / installed).touch()
    (shared_libs.SHARED_LIBS.root / "pyvenv.cfg").write_text(f"home = {home}\nversion = 3.14.0\n", encoding="utf-8")

    assert shared_libs.SHARED_LIBS.is_valid is expected


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("shared_pip_layout")
def test_shared_libs_validity_ignores_base_interpreter_off_windows() -> None:
    (shared_libs.SHARED_LIBS.root / "pyvenv.cfg").write_text("home = /nonexistent\n", encoding="utf-8")

    assert shared_libs.SHARED_LIBS.is_valid


@pytest.mark.parametrize(
    "pip_args",
    [
        pytest.param([], id="default"),
        pytest.param(["setuptools"], id="installed-with-pip"),
    ],
)
@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_excludes_setuptools(pip_args: list[str]) -> None:
    shared_libs.SHARED_LIBS.create(verbose=True, pip_args=pip_args)
    listing: Final[str] = subprocess.run(
        [str(shared_libs.SHARED_LIBS.python_path), "-m", "pip", "list", "--format=json"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    installed: Final[set[str]] = {pkg["name"].lower() for pkg in json.loads(listing)}
    assert ("pip" in installed, "setuptools" in installed) == (True, False)


@pytest.mark.skipif(sys.version_info < (3, 12), reason="venvs bundle setuptools before Python 3.12")
@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_create_does_not_warn_about_missing_setuptools(capfd: pytest.CaptureFixture[str]) -> None:
    shared_libs.SHARED_LIBS.create(verbose=False, pip_args=[])
    assert "Skipping setuptools" not in capfd.readouterr().err


@pytest.mark.skipif(sys.version_info < (3, 12), reason="venvs bundle setuptools before Python 3.12")
@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_create_skips_setuptools_uninstall_when_absent(mocker: MockerFixture) -> None:
    spy: Final[MagicMock] = mocker.patch("pipx.shared_libs.run_subprocess", autospec=True, side_effect=run_subprocess)

    shared_libs.SHARED_LIBS.create(pip_args=[], verbose=False)

    assert [call.args[0] for call in spy.call_args_list if "uninstall" in call.args[0]] == []


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_create_without_bundled_pip_wheel(mocker: MockerFixture) -> None:
    def hide_bundled_pip(
        cmd: Sequence[str | Path],
        *,
        log_cmd_str: str | None = None,
        log_stdout: bool = True,
        log_stderr: bool = True,
        run_dir: str | None = None,
        env_overrides: dict[str, str | None] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        process: Final[subprocess.CompletedProcess[str]] = run_subprocess(
            cmd,
            log_cmd_str=log_cmd_str,
            log_stdout=log_stdout,
            log_stderr=log_stderr,
            run_dir=run_dir,
            env_overrides=env_overrides,
        )
        if "--without-pip" in cmd:
            process.stdout = ""
        return process

    mocker.patch("pipx.shared_libs.run_subprocess", autospec=True, side_effect=hide_bundled_pip)

    shared_libs.SHARED_LIBS.create(pip_args=[], verbose=False)

    assert shared_libs.SHARED_LIBS.is_valid


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_create_preserves_pip_args() -> None:
    pip_args: Final[list[str]] = ["--disable-pip-version-check"]
    shared_libs.SHARED_LIBS.create(pip_args=pip_args, verbose=False)
    assert (pip_args, shared_libs.SHARED_LIBS.is_valid) == (["--disable-pip-version-check"], True)


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_create_without_index_when_auto_upgrade_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(shared_libs.DISABLE_SHARED_LIBS_AUTO_UPGRADE, "1")

    shared_libs.SHARED_LIBS.create(pip_args=["--no-index"], verbose=False)

    assert shared_libs.SHARED_LIBS.is_valid


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_global_install_creates_shared_libs_in_global_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_GLOBAL_SHARED_LIBS", None)

    assert not run_pipx_cli(["install", "--global", "pycowsay"])

    assert (shared_libs.SHARED_LIBS.root, shared_libs.SHARED_LIBS.is_valid) == (
        (tmp_path / "global" / "pipxhome" / "shared").resolve(),
        True,
    )


@pytest.fixture
def shared_pip_layout(pipx_ultra_temp_env: None) -> dict[str, Path]:  # ruff:ignore[unused-function-argument]  # required fixture dependency; usefixtures has no effect on fixtures
    # empty files stand in for pip, sparing a pip install per test
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", shared_libs.SHARED_LIBS.root], check=True)
    shared_libs.SHARED_LIBS.pip_path.touch()
    pip_main: Final[Path] = shared_libs.SHARED_LIBS.site_packages[0] / "pip" / "_internal" / "cli" / "main.py"
    pip_main.parent.mkdir(parents=True)
    pip_main.touch()
    return {
        "python": shared_libs.SHARED_LIBS.python_path,
        "pip-script": shared_libs.SHARED_LIBS.pip_path,
        "pip-module": pip_main,
    }


@pytest.mark.usefixtures("shared_pip_layout")
def test_shared_libs_validity_accepts_complete_layout() -> None:
    assert shared_libs.SHARED_LIBS.is_valid


@pytest.mark.parametrize(
    "removed",
    [
        pytest.param("python", id="python-missing"),
        pytest.param("pip-script", id="pip-script-missing"),
        pytest.param("pip-module", id="pip-module-missing"),
    ],
)
def test_shared_libs_validity_checks_files(shared_pip_layout: dict[str, Path], removed: str) -> None:
    shared_pip_layout[removed].unlink()

    assert not shared_libs.SHARED_LIBS.is_valid


def test_shared_libs_validity_check_is_cached(shared_pip_layout: dict[str, Path]) -> None:
    assert shared_libs.SHARED_LIBS.is_valid
    shared_pip_layout["pip-module"].unlink()

    assert shared_libs.SHARED_LIBS.is_valid


@pytest.mark.parametrize(
    ("version", "needs_upgrade"),
    [
        pytest.param("26.2.1", True, id="below-floor"),
        pytest.param("26.2.2", False, id="at-floor"),
    ],
)
@pytest.mark.usefixtures("shared_pip_layout")
def test_fresh_shared_pip_needs_upgrade_below_floor(version: str, *, needs_upgrade: bool) -> None:
    (dist_info := shared_libs.SHARED_LIBS.site_packages[0] / f"pip-{version}.dist-info").mkdir()
    (dist_info / "METADATA").write_text(f"Metadata-Version: 2.1\nName: pip\nVersion: {version}\n", encoding="utf-8")

    assert shared_libs.SHARED_LIBS.needs_upgrade is needs_upgrade


def test_install_rebuilds_shared_libs_missing_pip_before_running_pip(
    shared_pip_layout: dict[str, Path], caplog: pytest.LogCaptureFixture
) -> None:
    shared_pip_layout["pip-module"].unlink()

    return_code: Final[int] = run_pipx_cli(["install", "--backend", "pip", "pycowsay"])

    assert (return_code, "does not import" in caplog.text) == (0, False)


def _truncate_pip_main() -> None:
    (shared_libs.SHARED_LIBS.site_packages[0] / "pip" / "_internal" / "cli" / "main.py").write_text("")


def _remove_shared_libs() -> None:
    shutil.rmtree(shared_libs.SHARED_LIBS.root)


@pytest.mark.parametrize(
    "break_shared_libs",
    [pytest.param(_truncate_pip_main, id="truncated-pip-module"), pytest.param(_remove_shared_libs, id="removed")],
)
@pytest.mark.usefixtures("shared_pip_layout")
def test_install_rebuilds_shared_libs_broken_after_validation(break_shared_libs: Callable[[], None]) -> None:
    assert shared_libs.SHARED_LIBS.is_valid
    break_shared_libs()

    assert not run_pipx_cli(["install", "--backend", "pip", "pycowsay"])


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_install_failure_with_working_pip_keeps_shared_libs() -> None:
    shared_libs.SHARED_LIBS.create(pip_args=[], verbose=False)
    (sentinel := shared_libs.SHARED_LIBS.root / "sentinel").touch()

    return_code: Final[int] = run_pipx_cli(["install", "--backend", "pip", "pipx-package-does-not-exist"])

    assert (return_code, sentinel.exists()) == (1, True)


def test_shared_libs_upgrade_enforces_pip_floor(upgrade_subprocess: MagicMock) -> None:
    shared_libs.SHARED_LIBS.upgrade(pip_args=["pip==20"], verbose=True, raises=True)

    install_command: Final[list[str]] = upgrade_subprocess.call_args.args[0]
    assert (upgrade_subprocess.call_count, "pip==20" in install_command, "pip >= 26.2.2" in install_command) == (
        1,
        True,
        True,
    )


@pytest.fixture
def upgrade_subprocess(pipx_ultra_temp_env: None, mocker: MockerFixture) -> MagicMock:  # ruff:ignore[unused-function-argument]  # required fixture dependency; usefixtures has no effect on fixtures
    shared_libs.SHARED_LIBS.create(verbose=True, pip_args=[])
    shared_libs.SHARED_LIBS.has_been_updated_this_run = False
    return mocker.patch(
        "pipx.shared_libs.run_subprocess",
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
    )


def test_shared_libs_upgrade_runs_pip_in_shared_root(upgrade_subprocess: MagicMock) -> None:
    shared_libs.SHARED_LIBS.upgrade(pip_args=["--find-links", "wheels"], verbose=True, raises=True)

    assert upgrade_subprocess.call_args.kwargs["run_dir"] == str(shared_libs.SHARED_LIBS.root)


def test_shared_libs_upgrade_resolves_relative_cert_against_cwd(
    upgrade_subprocess: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    shared_libs.SHARED_LIBS.upgrade(pip_args=["--cert=ca.pem"], verbose=True, raises=True)

    assert f"--cert={(tmp_path / 'ca.pem').resolve()}" in upgrade_subprocess.call_args.args[0]


@pytest.mark.usefixtures("shared_pip_layout")
def test_shared_libs_upgrade_serializes_concurrent_calls(mocker: MockerFixture) -> None:
    first_started: Final[Event] = Event()
    release_first: Final[Event] = Event()
    second_started: Final[Event] = Event()

    def run_upgrade(
        _command: Sequence[str | Path], **_kwargs: dict[str, str | None] | None
    ) -> subprocess.CompletedProcess[str]:
        if first_started.is_set():
            second_started.set()
        else:
            first_started.set()
            if not release_first.wait(5):
                msg = "concurrent shared library test did not release the first upgrade"
                raise TimeoutError(msg)
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    mocker.patch("pipx.shared_libs.run_subprocess", autospec=True, side_effect=run_upgrade)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first_upgrade: Final = executor.submit(shared_libs.SHARED_LIBS.upgrade, pip_args=[], verbose=True, raises=True)
        assert first_started.wait(5)
        second_upgrade: Final = executor.submit(shared_libs.SHARED_LIBS.upgrade, pip_args=[], verbose=True, raises=True)
        try:
            assert not second_started.wait(0.5)
        finally:
            release_first.set()
        first_upgrade.result(timeout=5)
        second_upgrade.result(timeout=5)


@pytest.mark.parametrize(
    ("env_value", "expected_calls"),
    [
        pytest.param("1", 0, id="disabled"),
        pytest.param("0", 1, id="enabled"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_disable_shared_libs_auto_upgrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, env_value: str, expected_calls: int
) -> None:
    (site_packages := tmp_path / "venv" / "lib" / "python" / "site-packages").mkdir(parents=True)
    (site_packages / PIPX_SHARED_PTH).write_text("")
    venv: Final[Venv] = Venv(tmp_path / "venv")
    monkeypatch.setenv(shared_libs.DISABLE_SHARED_LIBS_AUTO_UPGRADE, env_value)
    monkeypatch.setattr(type(shared_libs.SHARED_LIBS), "is_valid", property(lambda _self: True))
    monkeypatch.setattr(type(shared_libs.SHARED_LIBS), "needs_upgrade", property(lambda _self: True))
    upgrade: Final[MagicMock] = mocker.patch.object(shared_libs.SHARED_LIBS, "upgrade", autospec=True)

    venv.check_upgrade_shared_libs(verbose=True, pip_args=[])

    assert upgrade.call_count == expected_calls


# rebuilds the shared libraries and reinstalls two venvs: just over 10 s on a free-threaded 2-core CI runner
@pytest.mark.timeout(60)
@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_reinstall_all_rebuilds_broken_shared_pip_once(caplog: pytest.LogCaptureFixture) -> None:
    for suffix in ("_a", "_b"):
        assert not run_pipx_cli(["install", "--backend", "pip", "pycowsay", f"--suffix={suffix}"])
    _truncate_pip_main()
    caplog.clear()

    exit_code: Final[int] = run_pipx_cli(["reinstall-all"])

    assert (exit_code, caplog.text.count("does not import")) == (0, 1)


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_runpip_skips_rebuild_when_another_process_repaired_shared_pip(
    mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    assert not run_pipx_cli(["install", "--backend", "pip", "pycowsay"])
    pip_main: Final[Path] = shared_libs.SHARED_LIBS.site_packages[0] / "pip" / "_internal" / "cli" / "main.py"
    source: Final[str] = pip_main.read_text()
    pip_main.write_text("")
    acquire: Final = FileLock.acquire

    def repaired_while_waiting(lock: FileLock) -> AcquireReturnProxy:
        if lock.lock_file.endswith(f"{shared_libs.SHARED_LIBS.root.name}.lock"):
            pip_main.write_text(source)
        return acquire(lock)

    mocker.patch.object(FileLock, "acquire", autospec=True, side_effect=repaired_while_waiting)
    caplog.clear()

    exit_code: Final[int] = run_pipx_cli(["runpip", "pycowsay", "list"])

    assert (exit_code, "does not import" in caplog.text) == (0, False)


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_install_cooldown_applies_to_new_shared_pip(package_cache_dir: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO")
    # pip filters an index by its upload-time metadata, which the test index lacks; local files pass the filter
    pip_args: Final[str] = f"--no-index --find-links={package_cache_dir}"

    assert not run_pipx_cli(["install", "--backend", "pip", "--cooldown", "7", f"--pip-args={pip_args}", "pycowsay"])

    assert [
        message.partition(" -m pip ")[2]
        for record in caplog.records
        if (message := record.getMessage()).startswith(f"running {shared_libs.SHARED_LIBS.python_path} -m pip")
        and " install " in message
    ] == [
        f"--no-input --disable-pip-version-check install --upgrade {pip_args} --force-reinstall -q pip == 26.2.2",
        f"--no-input --disable-pip-version-check install --upgrade {pip_args} --uploaded-prior-to P7D -q pip >= 26.2.2",
    ]


def test_shared_libs_upgrade_under_cooldown_filters_by_upload_time(upgrade_subprocess: MagicMock) -> None:
    with shared_libs.shared_pip_cooldown(7):
        shared_libs.SHARED_LIBS.upgrade(pip_args=[], verbose=True, raises=True)

    assert [call.args[0][5:] for call in upgrade_subprocess.call_args_list] == [
        ["install", "--upgrade", "--uploaded-prior-to", "P7D", "pip >= 26.2.2"]
    ]


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_create_under_cooldown_keeps_floor_when_index_lacks_upload_times() -> None:
    with shared_libs.shared_pip_cooldown(7):
        shared_libs.SHARED_LIBS.create(pip_args=[], verbose=False)

    assert sorted(path.name for path in shared_libs.SHARED_LIBS.site_packages[0].glob("pip-*.dist-info")) == [
        "pip-26.2.2.dist-info"
    ]
