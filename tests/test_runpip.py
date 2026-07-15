from __future__ import annotations

import json
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from helpers import run_pipx_cli, skip_if_windows
from pipx import paths

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.usefixtures("pipx_temp_env")
def test_runpip() -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["runpip", "pycowsay", "list"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_runpip_splits_single_argument() -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["runpip", "pycowsay", "list --format=freeze"])


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env")
def test_runpip_global() -> None:
    assert not run_pipx_cli(["install", "--global", "pycowsay"])
    assert not run_pipx_cli(["runpip", "--global", "pycowsay", "list"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_runpip_install_refreshes_main_package_metadata(empty_project: Path, tmp_path: Path) -> None:
    package_dir = empty_project
    wheel_dir = tmp_path / "wheelhouse"
    wheel_dir.mkdir()
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", str(package_dir), "--no-deps", "--wheel-dir", str(wheel_dir)],
        check=True,
    )
    wheel_path = next(wheel_dir.glob("empty_project-*.whl"))

    assert not run_pipx_cli(["install", "--editable", str(package_dir)])

    metadata_path = paths.ctx.venvs / "empty-project" / "pipx_metadata.json"
    before = json.loads(metadata_path.read_text())
    assert before["main_package"]["package_or_url"] == str(package_dir.resolve())
    assert before["main_package"]["pip_args"] == ["--editable"]

    assert not run_pipx_cli(["runpip", "empty-project", "install", "--force-reinstall", str(wheel_path)])

    after = json.loads(metadata_path.read_text())
    assert after["main_package"]["package_or_url"] == str(wheel_path.resolve())
    assert after["main_package"]["pip_args"] == []
