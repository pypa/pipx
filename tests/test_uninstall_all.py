from __future__ import annotations

import pytest

from helpers import PIPX_METADATA_LEGACY_VERSIONS, mock_legacy_venv, run_pipx_cli


@pytest.mark.usefixtures("pipx_temp_env", "capsys")
def test_uninstall_all() -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["uninstall-all"])


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
@pytest.mark.usefixtures("pipx_temp_env", "capsys")
def test_uninstall_all_legacy_venv(metadata_version: str | None) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    assert not run_pipx_cli(["uninstall-all"])
