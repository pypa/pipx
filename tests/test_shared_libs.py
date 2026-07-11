import json
import os
import subprocess
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from pipx import shared_libs
from pipx.constants import PIPX_SHARED_PTH, WINDOWS
from pipx.venv import Venv


@pytest.mark.parametrize(
    "mtime_minus_now,needs_upgrade",
    [
        (-shared_libs.SHARED_LIBS_MAX_AGE_SEC - 5 * 60, True),
        (-shared_libs.SHARED_LIBS_MAX_AGE_SEC + 5 * 60, False),
    ],
)
def test_auto_update_shared_libs(capsys, pipx_ultra_temp_env, mtime_minus_now, needs_upgrade):
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

    assert shared_libs._venv_python_is_valid(python_exe) is False


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

    assert shared_libs._venv_python_is_valid(python_exe) is True


def test_shared_libs_excludes_setuptools(pipx_ultra_temp_env: None) -> None:
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


def test_shared_libs_create_preserves_pip_args(pipx_ultra_temp_env: None) -> None:
    pip_args = ["--disable-pip-version-check"]
    shared_libs.shared_libs.create(pip_args=pip_args)
    assert (pip_args, shared_libs.shared_libs.is_valid) == (["--disable-pip-version-check"], True)


def test_venv_python_is_valid_non_windows() -> None:
    """Test that _venv_python_is_valid always returns True on non-Windows platforms."""
    with patch.object(shared_libs, "WINDOWS", False):
        # Should return True regardless of the path
        assert shared_libs._venv_python_is_valid(Path("/fake/path/python")) is True


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
        property(lambda self: True),
    )
    monkeypatch.setattr(
        type(shared_libs.shared_libs),
        "needs_upgrade",
        property(lambda self: True),
    )
    monkeypatch.setattr(
        shared_libs.shared_libs,
        "upgrade",
        lambda **kwargs: upgrade_calls.append(kwargs),
    )

    venv.check_upgrade_shared_libs(verbose=True, pip_args=[], force_upgrade=force_upgrade)

    assert len(upgrade_calls) == expected_calls
