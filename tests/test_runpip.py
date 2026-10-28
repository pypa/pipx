from __future__ import annotations

import json
from typing import TYPE_CHECKING, Final

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


@pytest.mark.parametrize(
    ("backend", "option_args"),
    [
        pytest.param("pip", (), id="pip-no-option"),
        pytest.param("pip", ("--only-binary", "empty-project"), id="pip-only-binary"),
        pytest.param("pip", ("--no-binary", "empty-project"), id="pip-no-binary"),
        pytest.param("pip", ("--proxy", "empty-project"), id="pip-proxy"),
        pytest.param("uv", ("-P", "empty-project"), id="uv-upgrade-package"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_runpip_install_refreshes_main_package_metadata(
    empty_project: Path, empty_project_wheel: Path, backend: str, option_args: tuple[str, ...]
) -> None:
    assert not run_pipx_cli(["install", "--backend", backend, "--editable", str(empty_project)])

    metadata_path = paths.ctx.venvs / "empty-project" / "pipx_metadata.json"
    before = json.loads(metadata_path.read_text())
    assert before["main_package"]["package_or_url"] == str(empty_project.resolve())
    assert before["main_package"]["pip_args"] == ["--editable"]

    assert not run_pipx_cli([
        "runpip",
        "empty-project",
        "install",
        "--force-reinstall",
        *option_args,
        str(empty_project_wheel),
    ])

    after = json.loads(metadata_path.read_text())
    assert after["main_package"]["package_or_url"] == str(empty_project_wheel.resolve())
    assert after["main_package"]["pip_args"] == []


_NEW_INDEX: Final[tuple[str, ...]] = ("--no-index", "--find-links", "{new}")


@pytest.mark.parametrize("backend", ["pip", "uv"])
@pytest.mark.parametrize(
    ("install_index_args", "runpip_index_args"),
    [
        pytest.param((), _NEW_INDEX, id="record"),
        pytest.param(("--find-links", "{old}"), _NEW_INDEX, id="replace"),
        pytest.param(("--find-links", "{old}"), (), id="keep"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_runpip_install_records_index_options(
    empty_project: Path,
    empty_project_wheel: Path,
    backend: str,
    install_index_args: tuple[str, ...],
    runpip_index_args: tuple[str, ...],
) -> None:
    links = {"old": str(empty_project.parent), "new": str(empty_project_wheel.parent)}
    pip_args = [f"--pip-args={' '.join(install_index_args).format_map(links)}"] if install_index_args else []
    assert not run_pipx_cli(["install", "--backend", backend, *pip_args, "--editable", str(empty_project)])

    assert not run_pipx_cli([
        "runpip",
        "empty-project",
        "install",
        "--force-reinstall",
        *(arg.format_map(links) for arg in runpip_index_args),
        "empty-project" if runpip_index_args else str(empty_project_wheel),
    ])

    metadata = json.loads((paths.ctx.venvs / "empty-project" / "pipx_metadata.json").read_text())
    expected = [arg.format_map(links) for arg in runpip_index_args or install_index_args]
    assert metadata["main_package"]["pip_args"] == expected
