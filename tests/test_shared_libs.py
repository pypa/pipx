import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest  # type: ignore[import-not-found]

from pipx import shared_libs
from pipx.constants import WINDOWS


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


def test_venv_python_is_valid_non_windows() -> None:
    """Test that _venv_python_is_valid always returns True on non-Windows platforms."""
    with patch.object(shared_libs, "WINDOWS", False):
        # Should return True regardless of the path
        assert shared_libs._venv_python_is_valid(Path("/fake/path/python")) is True
