from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from helpers import run_pipx_cli, skip_if_windows
from pipx import paths
from pipx.commands.common import (
    _remove_stale_venv_resources,  # noqa: PLC2701  # test exercises private helper, no public API
    _copy_launcher_targets_venv,
    expose_resources_globally,
    get_exposed_paths_for_package,
)
from pipx.venv import Venv

if TYPE_CHECKING:
    from pathlib import Path


@skip_if_windows
def test_get_exposed_paths_ignores_recursive_symlink(tmp_path: Path) -> None:
    venv_resource_path = tmp_path / "venv_bin"
    venv_resource_path.mkdir()
    local_resource_dir = tmp_path / "bin"
    local_resource_dir.mkdir()
    loop = local_resource_dir / "recursiveexample"
    loop.symlink_to(loop.name)

    exposed = get_exposed_paths_for_package(venv_resource_path, local_resource_dir)

    assert loop not in exposed


@skip_if_windows
def test_expose_app_scripts_ignores_pythonpath(tmp_path: Path) -> None:
    venv_resource_path = tmp_path / "venv_bin"
    venv_resource_path.mkdir()
    local_resource_dir = tmp_path / "bin"
    shadow_path = tmp_path / "shadow"
    shadow_path.mkdir()

    app_path = venv_resource_path / "demo"
    app_path.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        f"if {str(shadow_path)!r} in sys.path:\n"
        "    raise SystemExit('PYTHONPATH leaked into app script')\n"
        "print('ok')\n"
    )
    app_path.chmod(0o755)

    expose_resources_globally("app", local_resource_dir, [app_path], force=False)

    assert app_path.read_text().splitlines()[0] == f"#!{sys.executable} -E"

    result = subprocess.run(
        [app_path],
        check=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(shadow_path)},
        text=True,
    )
    assert result.stdout == "ok\n"


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env")
def test_remove_stale_venv_resources_keeps_files_pipx_does_not_own(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["install", "pycowsay"]) == 0
    capsys.readouterr()
    venv = Venv(paths.ctx.venvs / "pycowsay")
    bin_dir = paths.ctx.bin_dir

    owned = bin_dir / "stale-owned"
    owned.symlink_to(venv.pipx_metadata.main_package.app_paths[0])
    replaced = bin_dir / "stale-replaced"
    replaced.write_text("belongs to the user")

    _remove_stale_venv_resources({owned, replaced}, venv, bin_dir, paths.ctx.man_dir)

    assert (owned.exists(), replaced.read_text()) == (False, "belongs to the user")


def test_copy_launcher_targets_venv_unicode_decode_error(tmp_path: Path) -> None:
    """_copy_launcher_targets_venv returns False for non-UTF8 file."""
    venv_resource_path = tmp_path / "venv_bin"
    venv_resource_path.mkdir()
    local_resource_dir = tmp_path / "bin"
    local_resource_dir.mkdir()

    # Create a non-UTF8 file in the local bin directory
    non_utf8_file = local_resource_dir / "weird.exe"
    non_utf8_file.write_bytes(b'\xff\xfe')  # Invalid UTF-8

    # Should return False without raising UnicodeDecodeError
    assert not _copy_launcher_targets_venv(non_utf8_file, venv_resource_path)


def test_copy_launcher_targets_venv_valid_launcher(tmp_path: Path) -> None:
    """_copy_launcher_targets_venv returns True for a launcher pointing to venv."""
    venv_resource_path = tmp_path / "venv_bin"
    venv_resource_path.mkdir()
    local_resource_dir = tmp_path / "bin"
    local_resource_dir.mkdir()

    # Create a launcher with a shebang pointing to the venv's python
    launcher = local_resource_dir / "myapp"
    shebang = f"#!{venv_resource_path / 'python'}\nprint('hello')"
    launcher.write_text(shebang, encoding="utf-8")
    launcher.chmod(0o755)

    # Should return True
    assert _copy_launcher_targets_venv(launcher, venv_resource_path)


def test_copy_launcher_targets_venv_launcher_pointing_outside(tmp_path: Path) -> None:
    """_copy_launcher_targets_venv returns False for launcher pointing outside venv."""
    venv_resource_path = tmp_path / "venv_bin"
    venv_resource_path.mkdir()
    local_resource_dir = tmp_path / "bin"
    local_resource_dir.mkdir()
    other_dir = tmp_path / "other"
    other_dir.mkdir()

    # Create a launcher with a shebang pointing to another directory
    launcher = local_resource_dir / "myapp"
    shebang = f"#!{other_dir / 'python'}\nprint('hello')"
    launcher.write_text(shebang, encoding="utf-8")
    launcher.chmod(0o755)

    # Should return False
    assert not _copy_launcher_targets_venv(launcher, venv_resource_path)
