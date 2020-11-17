import pytest  # type: ignore

from helpers import mock_legacy_venv, run_pipx_cli


def test_upgrade_all(pipx_temp_env, capsys):
    assert run_pipx_cli(["upgrade", "pycowsay"])
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["upgrade-all"])


@pytest.mark.parametrize("metadata_version", [None, "0.1"])
def test_upgrade_all_legacy_venv(pipx_temp_env, capsys, caplog, metadata_version):
    if metadata_version is None:
        assert run_pipx_cli(["upgrade", "pycowsay"])
        assert not run_pipx_cli(["install", "pycowsay"])
        mock_legacy_venv("pycowsay", metadata_version=metadata_version)
        capsys.readouterr()
        assert run_pipx_cli(["upgrade-all"])
        # TODO: fix assertion for caplog
        # assert "Error encountered when upgrading pycowsay" in captured.err
    else:
        assert run_pipx_cli(["upgrade", "pycowsay"])
        assert not run_pipx_cli(["install", "pycowsay"])
        mock_legacy_venv("pycowsay", metadata_version=metadata_version)
        assert not run_pipx_cli(["upgrade-all"])
