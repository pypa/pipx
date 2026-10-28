from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING, Final
from unittest.mock import patch

import pytest
from filelock import AcquireReturnProxy, FileLock

from helpers import PACKAGE_CACHE_DIR_NAME, run_pipx_cli, skip_if_windows
from pipx import paths, shared_libs
from pipx.backends.pip import PipBackend
from pipx.constants import PIPX_SHARED_PTH, WINDOWS
from pipx.util import run_subprocess
from pipx.venv import Venv

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from pytest_mock import MockerFixture


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_create_venv_lists_every_shared_site_packages_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # purelib and platlib coincide on the platforms CI runs, so pin a split layout to keep both lines under test
    shared_site_packages = [tmp_path / "shared" / "purelib", tmp_path / "shared" / "platlib"]
    monkeypatch.setattr(type(shared_libs.shared_libs), "site_packages", property(lambda _self: shared_site_packages))
    venv_root = tmp_path / "venv"

    PipBackend().create_venv(
        venv_root, python=sys.executable, venv_args=[], pip_args=[], include_pip=False, verbose=False
    )

    pth_file = next(venv_root.glob(f"**/{PIPX_SHARED_PTH}"))
    assert pth_file.read_text().splitlines() == [str(path) for path in shared_site_packages]


@pytest.mark.parametrize(
    ("mtime_minus_now", "needs_upgrade"),
    [
        (-shared_libs.SHARED_LIBS_MAX_AGE_SEC - 5 * 60, True),
        (-shared_libs.SHARED_LIBS_MAX_AGE_SEC + 5 * 60, False),
    ],
)
@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_auto_update_shared_libs(mtime_minus_now: float, needs_upgrade: bool) -> None:
    now = time.time()
    shared_libs.shared_libs.create(verbose=True, pip_args=[])
    shared_libs.shared_libs.has_been_updated_this_run = False

    access_time = now  # this can be anything
    os.utime(shared_libs.shared_libs.pip_path, (access_time, mtime_minus_now + now))

    assert shared_libs.shared_libs.needs_upgrade is needs_upgrade


@pytest.mark.skipif(not WINDOWS, reason="Windows-specific test")
def test_venv_python_is_valid_missing_interpreter(tmp_path: Path) -> None:
    """Test that _venv_python_is_valid returns False when the underlying Python is missing."""
    # Create a fake venv structure
    venv_path = tmp_path / "test_venv"
    scripts_path = venv_path / "Scripts"
    scripts_path.mkdir(parents=True)
    python_exe = scripts_path / "python.exe"
    python_exe.touch()

    # Create a pyvenv.cfg pointing to a non-existent Python
    pyvenv_cfg = venv_path / "pyvenv.cfg"
    pyvenv_cfg.write_text("home = C:\\NonExistent\\Python\\Path\nversion = 3.14.0\n")

    assert shared_libs._venv_python_is_valid(python_exe) is False  # ruff:ignore[private-member-access]  # private helper under test has no public wrapper


@pytest.mark.skipif(not WINDOWS, reason="Windows-specific test")
def test_venv_python_is_valid_existing_interpreter(tmp_path: Path) -> None:
    """Test that _venv_python_is_valid returns True when the underlying Python exists."""
    # Create a fake venv structure
    venv_path = tmp_path / "test_venv"
    scripts_path = venv_path / "Scripts"
    scripts_path.mkdir(parents=True)
    python_exe = scripts_path / "python.exe"
    python_exe.touch()

    # Create the "original" Python installation
    original_python_dir = tmp_path / "original_python"
    original_python_dir.mkdir()
    original_python_exe = original_python_dir / "python.exe"
    original_python_exe.touch()

    # Create a pyvenv.cfg pointing to the existing Python
    pyvenv_cfg = venv_path / "pyvenv.cfg"
    pyvenv_cfg.write_text(f"home = {original_python_dir}\nversion = 3.12.0\n")

    assert shared_libs._venv_python_is_valid(python_exe) is True  # ruff:ignore[private-member-access]  # private helper under test has no public wrapper


@pytest.mark.parametrize(
    "pip_args",
    [
        pytest.param([], id="default"),
        pytest.param(["setuptools"], id="installed-with-pip"),
    ],
)
@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_excludes_setuptools(pip_args: list[str]) -> None:
    shared_libs.shared_libs.create(verbose=True, pip_args=pip_args)
    result = subprocess.run(
        [str(shared_libs.shared_libs.python_path), "-m", "pip", "list", "--format=json"],
        capture_output=True,
        text=True,
        check=True,
    )
    installed = {pkg["name"].lower() for pkg in json.loads(result.stdout)}
    assert "pip" in installed
    assert "setuptools" not in installed


@pytest.mark.skipif(sys.version_info < (3, 12), reason="venvs bundle setuptools before Python 3.12")
@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_create_does_not_warn_about_missing_setuptools(capfd: pytest.CaptureFixture[str]) -> None:
    shared_libs.shared_libs.create(verbose=False, pip_args=[])
    assert "Skipping setuptools" not in capfd.readouterr().err


@pytest.mark.skipif(sys.version_info < (3, 12), reason="venvs bundle setuptools before Python 3.12")
@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_create_skips_setuptools_uninstall_when_absent(mocker: MockerFixture) -> None:
    spy = mocker.patch("pipx.shared_libs.run_subprocess", autospec=True, side_effect=run_subprocess)

    shared_libs.shared_libs.create(pip_args=[])

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
        process = run_subprocess(
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

    shared_libs.shared_libs.create(pip_args=[])

    assert shared_libs.shared_libs.is_valid


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_create_preserves_pip_args() -> None:
    pip_args = ["--disable-pip-version-check"]
    shared_libs.shared_libs.create(pip_args=pip_args)
    assert (pip_args, shared_libs.shared_libs.is_valid) == (["--disable-pip-version-check"], True)


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_create_without_index_when_auto_upgrade_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(shared_libs.DISABLE_SHARED_LIBS_AUTO_UPGRADE, "1")

    shared_libs.shared_libs.create(pip_args=["--no-index"])

    assert shared_libs.shared_libs.is_valid


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env")
def test_global_install_creates_shared_libs_in_global_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(paths, "OVERRIDE_PIPX_GLOBAL_SHARED_LIBS", None)

    assert not run_pipx_cli(["install", "--global", "pycowsay"])

    expected_root = (tmp_path / "global" / "pipxhome" / "shared").resolve()
    assert (shared_libs.shared_libs.root, shared_libs.shared_libs.is_valid) == (expected_root, True)


@pytest.fixture
def shared_pip_layout(pipx_ultra_temp_env: None) -> dict[str, Path]:  # ruff:ignore[unused-function-argument]  # required fixture dependency; usefixtures has no effect on fixtures
    # empty files stand in for pip, sparing a pip install per test
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", shared_libs.shared_libs.root], check=True)
    shared_libs.shared_libs.pip_path.touch()
    pip_main = shared_libs.shared_libs.site_packages[0] / "pip" / "_internal" / "cli" / "main.py"
    pip_main.parent.mkdir(parents=True)
    pip_main.touch()
    return {
        "python": shared_libs.shared_libs.python_path,
        "pip-script": shared_libs.shared_libs.pip_path,
        "pip-module": pip_main,
    }


@pytest.mark.parametrize(
    ("removed", "expected"),
    [
        pytest.param(None, True, id="complete"),
        pytest.param("python", False, id="python-missing"),
        pytest.param("pip-script", False, id="pip-script-missing"),
        pytest.param("pip-module", False, id="pip-module-missing"),
    ],
)
def test_shared_libs_validity_checks_files(
    shared_pip_layout: dict[str, Path], removed: str | None, expected: bool
) -> None:
    if removed is not None:
        shared_pip_layout[removed].unlink()

    assert shared_libs.shared_libs.is_valid is expected


def test_shared_libs_validity_check_is_cached(shared_pip_layout: dict[str, Path]) -> None:
    assert shared_libs.shared_libs.is_valid
    shared_pip_layout["pip-module"].unlink()

    assert shared_libs.shared_libs.is_valid


@pytest.mark.parametrize(
    ("version", "needs_upgrade"),
    [
        pytest.param("26.2.1", True, id="below-floor"),
        pytest.param("26.2.2", False, id="at-floor"),
    ],
)
@pytest.mark.usefixtures("shared_pip_layout")
def test_fresh_shared_pip_needs_upgrade_below_floor(version: str, *, needs_upgrade: bool) -> None:
    (dist_info := shared_libs.shared_libs.site_packages[0] / f"pip-{version}.dist-info").mkdir()
    (dist_info / "METADATA").write_text(f"Metadata-Version: 2.1\nName: pip\nVersion: {version}\n", encoding="utf-8")

    assert shared_libs.shared_libs.needs_upgrade is needs_upgrade


def test_install_rebuilds_shared_libs_missing_pip_before_running_pip(
    shared_pip_layout: dict[str, Path], caplog: pytest.LogCaptureFixture
) -> None:
    shared_pip_layout["pip-module"].unlink()

    return_code = run_pipx_cli(["install", "--backend", "pip", "pycowsay"])

    assert (return_code, "does not import" in caplog.text) == (0, False)


def _truncate_pip_main() -> None:
    (shared_libs.shared_libs.site_packages[0] / "pip" / "_internal" / "cli" / "main.py").write_text("")


def _remove_shared_libs() -> None:
    shutil.rmtree(shared_libs.shared_libs.root)


@pytest.mark.parametrize(
    "break_shared_libs",
    [pytest.param(_truncate_pip_main, id="truncated-pip-module"), pytest.param(_remove_shared_libs, id="removed")],
)
@pytest.mark.usefixtures("shared_pip_layout")
def test_install_rebuilds_shared_libs_broken_after_validation(break_shared_libs: Callable[[], None]) -> None:
    assert shared_libs.shared_libs.is_valid
    break_shared_libs()

    assert not run_pipx_cli(["install", "--backend", "pip", "pycowsay"])


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_install_failure_with_working_pip_keeps_shared_libs() -> None:
    shared_libs.shared_libs.create(pip_args=[])
    (sentinel := shared_libs.shared_libs.root / "sentinel").touch()

    return_code = run_pipx_cli(["install", "--backend", "pip", "pipx-package-does-not-exist"])

    assert (return_code, sentinel.exists()) == (1, True)


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_upgrade_enforces_pip_floor(
    mocker: MockerFixture,
) -> None:
    shared_libs.shared_libs.create(verbose=True, pip_args=[])
    shared_libs.shared_libs.has_been_updated_this_run = False
    run_subprocess = mocker.patch(
        "pipx.shared_libs.run_subprocess",
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
    )

    shared_libs.shared_libs.upgrade(pip_args=["pip==20"], verbose=True, raises=True)

    install_command = run_subprocess.call_args.args[0]
    run_subprocess.assert_called_once()
    assert "pip==20" in install_command
    assert "pip >= 26.2.2" in install_command


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_upgrade_runs_pip_in_shared_root(mocker: MockerFixture) -> None:
    shared_libs.shared_libs.create(verbose=True, pip_args=[])
    shared_libs.shared_libs.has_been_updated_this_run = False
    run_subprocess = mocker.patch(
        "pipx.shared_libs.run_subprocess",
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
    )

    shared_libs.shared_libs.upgrade(pip_args=["--find-links", "wheels"], verbose=True, raises=True)

    assert run_subprocess.call_args.kwargs["run_dir"] == str(shared_libs.shared_libs.root)


@pytest.mark.usefixtures("shared_pip_layout")
def test_shared_libs_upgrade_serializes_concurrent_calls(
    mocker: MockerFixture,
) -> None:
    first_started = Event()
    release_first = Event()
    second_started = Event()

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
        first_upgrade = executor.submit(shared_libs.shared_libs.upgrade, pip_args=[], verbose=True, raises=True)
        assert first_started.wait(5)
        second_upgrade = executor.submit(shared_libs.shared_libs.upgrade, pip_args=[], verbose=True, raises=True)
        try:
            assert not second_started.wait(0.5)
        finally:
            release_first.set()
        first_upgrade.result(timeout=5)
        second_upgrade.result(timeout=5)


def test_venv_python_is_valid_non_windows() -> None:
    """Test that _venv_python_is_valid always returns True on non-Windows platforms."""
    with patch.object(shared_libs, "WINDOWS", False):
        # Should return True regardless of the path
        assert shared_libs._venv_python_is_valid(Path("/fake/path/python")) is True  # ruff:ignore[private-member-access]  # private helper under test has no public wrapper


@pytest.mark.parametrize(
    ("env_value", "expected_calls"),
    [
        ("1", 0),
        ("0", 1),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_disable_shared_libs_auto_upgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    env_value: str,
    expected_calls: int,
) -> None:
    venv_path = tmp_path / "venv"
    site_packages = venv_path / "lib" / "python" / "site-packages"
    site_packages.mkdir(parents=True)
    (site_packages / PIPX_SHARED_PTH).write_text("")
    venv = Venv(venv_path)

    upgrade_calls = []
    monkeypatch.setenv(shared_libs.DISABLE_SHARED_LIBS_AUTO_UPGRADE, env_value)
    monkeypatch.setattr(
        type(shared_libs.shared_libs),
        "is_valid",
        property(lambda _self: True),
    )
    monkeypatch.setattr(
        type(shared_libs.shared_libs),
        "needs_upgrade",
        property(lambda _self: True),
    )
    monkeypatch.setattr(
        shared_libs.shared_libs,
        "upgrade",
        lambda **kwargs: upgrade_calls.append(kwargs),
    )

    venv.check_upgrade_shared_libs(verbose=True, pip_args=[])

    assert len(upgrade_calls) == expected_calls


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
    pip_main: Final[Path] = shared_libs.shared_libs.site_packages[0] / "pip" / "_internal" / "cli" / "main.py"
    source: Final[str] = pip_main.read_text()
    pip_main.write_text("")
    acquire: Final = FileLock.acquire

    def repaired_while_waiting(lock: FileLock) -> AcquireReturnProxy:
        if lock.lock_file.endswith(f"{shared_libs.shared_libs.root.name}.lock"):
            pip_main.write_text(source)
        return acquire(lock)

    mocker.patch.object(FileLock, "acquire", autospec=True, side_effect=repaired_while_waiting)
    caplog.clear()

    exit_code: Final[int] = run_pipx_cli(["runpip", "pycowsay", "list"])

    assert (exit_code, "does not import" in caplog.text) == (0, False)


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_install_cooldown_applies_to_new_shared_pip(root: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO")
    # pip filters an index by its upload-time metadata, which the test index lacks; local files pass the filter
    pip_args: Final[str] = f"--no-index --find-links={root / '.pipx_tests' / 'package_cache' / PACKAGE_CACHE_DIR_NAME}"

    assert not run_pipx_cli(["install", "--backend", "pip", "--cooldown", "7", f"--pip-args={pip_args}", "pycowsay"])

    assert [
        message.partition(" -m pip ")[2]
        for record in caplog.records
        if (message := record.getMessage()).startswith(f"running {shared_libs.shared_libs.python_path} -m pip")
        and " install " in message
    ] == [
        f"--no-input --disable-pip-version-check install --upgrade {pip_args} --force-reinstall -q pip == 26.2.2",
        f"--no-input --disable-pip-version-check install --upgrade {pip_args} --uploaded-prior-to P7D -q pip >= 26.2.2",
    ]


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_upgrade_under_cooldown_filters_by_upload_time(mocker: MockerFixture) -> None:
    shared_libs.shared_libs.create(verbose=True, pip_args=[])
    shared_libs.shared_libs.has_been_updated_this_run = False
    run_subprocess = mocker.patch(
        "pipx.shared_libs.run_subprocess",
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
    )

    with shared_libs.shared_pip_cooldown(7):
        shared_libs.shared_libs.upgrade(pip_args=[], verbose=True, raises=True)

    assert [call.args[0][5:] for call in run_subprocess.call_args_list] == [
        ["install", "--upgrade", "--uploaded-prior-to", "P7D", "pip >= 26.2.2"]
    ]


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_create_under_cooldown_keeps_floor_when_index_lacks_upload_times() -> None:
    with shared_libs.shared_pip_cooldown(7):
        shared_libs.shared_libs.create(pip_args=[])

    assert sorted(path.name for path in shared_libs.shared_libs.site_packages[0].glob("pip-*.dist-info")) == [
        "pip-26.2.2.dist-info"
    ]
