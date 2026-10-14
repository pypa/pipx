from __future__ import annotations

import json
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
def test_runpip_install_refreshes_main_package_metadata(empty_project: Path, empty_project_wheel: Path) -> None:
    assert not run_pipx_cli(["install", "--editable", str(empty_project)])

    metadata_path = paths.ctx.venvs / "empty-project" / "pipx_metadata.json"
    before = json.loads(metadata_path.read_text())
    assert before["main_package"]["package_or_url"] == str(empty_project.resolve())
    assert before["main_package"]["pip_args"] == ["--editable"]

    assert not run_pipx_cli(["runpip", "empty-project", "install", "--force-reinstall", str(empty_project_wheel)])

    after = json.loads(metadata_path.read_text())
    assert after["main_package"]["package_or_url"] == str(empty_project_wheel.resolve())
    assert after["main_package"]["pip_args"] == []
