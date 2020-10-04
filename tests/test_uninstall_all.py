import pytest  # type: ignore

from helpers import mock_legacy_venv, run_pipx_cli


def test_uninstall_all(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["uninstall-all"])


@pytest.mark.parametrize("metadata_version", [None, "0.1"])
def test_uninstall_all_legacy_venv(pipx_temp_env, capsys, metadata_version):
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    assert not run_pipx_cli(["uninstall-all"])
