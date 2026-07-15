from __future__ import annotations

import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from pipx import shared_libs
from pipx.constants import PIPX_SHARED_PTH, WINDOWS
from pipx.venv import Venv

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pytest_mock import MockerFixture


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

    assert shared_libs._venv_python_is_valid(python_exe) is False  # noqa: SLF001  # private helper under test has no public wrapper


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

    assert shared_libs._venv_python_is_valid(python_exe) is True  # noqa: SLF001  # private helper under test has no public wrapper


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_excludes_setuptools() -> None:
    shared_libs.shared_libs.create(verbose=True, pip_args=[])
    result = subprocess.run(
        [str(shared_libs.shared_libs.python_path), "-m", "pip", "list", "--format=json"],
        capture_output=True,
        text=True,
        check=True,
    )
    installed = {pkg["name"].lower() for pkg in json.loads(result.stdout)}
    assert "pip" in installed
    assert "setuptools" not in installed


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


@pytest.mark.parametrize(
    ("returncode", "expected"),
    [
        pytest.param(0, True, id="valid"),
        pytest.param(1, False, id="broken-pip"),
    ],
)
@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_validity_check_is_cached(
    mocker: MockerFixture,
    returncode: int,
    expected: bool,
) -> None:
    shared_libs.shared_libs.python_path.parent.mkdir(parents=True)
    shared_libs.shared_libs.python_path.touch()
    shared_libs.shared_libs.pip_path.touch()
    run_subprocess = mocker.patch(
        "pipx.shared_libs.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=[], returncode=returncode, stdout="", stderr=""),
    )

    assert (shared_libs.shared_libs.is_valid, shared_libs.shared_libs.is_valid) == (expected, expected)
    run_subprocess.assert_called_once()


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
    assert "pip >= 26.1" in install_command


@pytest.mark.usefixtures("pipx_ultra_temp_env")
def test_shared_libs_upgrade_serializes_concurrent_calls(
    mocker: MockerFixture,
) -> None:
    shared_libs.shared_libs.create(verbose=True, pip_args=[])
    shared_libs.shared_libs.has_been_updated_this_run = False
    first_started = Event()
    release_first = Event()
    second_started = Event()

    def run_upgrade(_command: Sequence[str | Path]) -> subprocess.CompletedProcess[str]:
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
        assert shared_libs._venv_python_is_valid(Path("/fake/path/python")) is True  # noqa: SLF001  # private helper under test has no public wrapper


@pytest.mark.parametrize(
    ("env_value", "force_upgrade", "expected_calls"),
    [
        ("1", False, 0),
        ("1", True, 1),
        ("0", False, 1),
    ],
)
def test_disable_shared_libs_auto_upgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    env_value: str,
    force_upgrade: bool,
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

    venv.check_upgrade_shared_libs(verbose=True, pip_args=[], force_upgrade=force_upgrade)

    assert len(upgrade_calls) == expected_calls
