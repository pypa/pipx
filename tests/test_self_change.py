from __future__ import annotations

import importlib
from dataclasses import replace
from typing import TYPE_CHECKING, Final

import pytest

from helpers import run_pipx_cli, write_import_probe
from package_info import PKG
from pipx import paths
from pipx.pipx_metadata_file import PipxMetadata

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


@pytest.mark.parametrize(
    ("package", "command"),
    [
        pytest.param("pycowsay", ["upgrade", "pycowsay"], id="upgrade"),
        pytest.param(PKG["black"]["spec"], ["upgrade-all"], id="upgrade-all"),
        pytest.param("pycowsay", ["install", "--force", "pycowsay"], id="install-force"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_self_change_imports_submodules_of_the_running_version(
    run_from_venv: Callable[[Path], None], package: str, command: list[str]
) -> None:
    assert not run_pipx_cli(["install", package])
    venv_dir: Final[Path] = paths.CTX.venvs / package.partition("==")[0]
    run_from_venv(venv_dir)

    assert not run_pipx_cli(command)
    write_import_probe(venv_dir, "new")

    assert importlib.import_module("running_probe.late").VALUE == "old"


@pytest.mark.usefixtures("pipx_temp_env")
def test_self_upgrade_failure_imports_from_the_restored_venv(
    run_from_venv: Callable[[Path], None], tmp_path: Path
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    venv_dir: Final[Path] = paths.CTX.venvs / "pycowsay"
    run_from_venv(venv_dir)
    metadata: Final[PipxMetadata] = PipxMetadata(venv_dir)
    metadata.main_package = replace(metadata.main_package, package_or_url=str(tmp_path / "missing"))
    metadata.write()

    assert run_pipx_cli(["upgrade", "pycowsay"])

    assert importlib.import_module("running_probe.late").VALUE == "old"
