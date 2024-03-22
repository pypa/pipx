import sys

import pytest  # type: ignore

from helpers import PIPX_METADATA_LEGACY_VERSIONS, mock_legacy_venv, run_pipx_cli
from pipx import shared_libs


def test_reinstall_all(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["reinstall-all", "--python", sys.executable])


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
def test_reinstall_all_legacy_venv(pipx_temp_env, capsys, metadata_version):
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)

    assert not run_pipx_cli(["reinstall-all", "--python", sys.executable])


def test_reinstall_all_suffix(pipx_temp_env, capsys):
    suffix = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])

    assert not run_pipx_cli(["reinstall-all", "--python", sys.executable])


@pytest.mark.parametrize("metadata_version", ["0.1"])
def test_reinstall_all_suffix_legacy_venv(pipx_temp_env, capsys, metadata_version):
    suffix = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])
    mock_legacy_venv(f"pycowsay{suffix}", metadata_version=metadata_version)

    assert not run_pipx_cli(["reinstall-all", "--python", sys.executable])


def test_reinstall_all_triggers_shared_libs_upgrade(pipx_temp_env, caplog, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])

    shared_libs.shared_libs.has_been_updated_this_run = False
    caplog.clear()

    assert not run_pipx_cli(["reinstall-all"])
    assert "Upgrading shared libraries in" in caplog.text
