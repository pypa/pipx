import pytest  # type: ignore[import-not-found]

from helpers import PIPX_METADATA_LEGACY_VERSIONS, mock_legacy_venv, run_pipx_cli


def test_upgrade_all(pipx_temp_env, capsys):
    assert run_pipx_cli(["upgrade", "pycowsay"])
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["upgrade-all"])


def test_upgrade_all_none(pipx_temp_env, capsys):
    assert not run_pipx_cli(["upgrade-all"])
    captured = capsys.readouterr()
    assert "No packages upgraded after running 'pipx upgrade-all'" in captured.out


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
def test_upgrade_all_legacy_venv(pipx_temp_env, capsys, caplog, metadata_version):
    assert run_pipx_cli(["upgrade", "pycowsay"])
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    if metadata_version is None:
        capsys.readouterr()
        assert run_pipx_cli(["upgrade-all"])
        assert "The following package(s) failed to upgrade: pycowsay" in caplog.text
    else:
        assert not run_pipx_cli(["upgrade-all"])
