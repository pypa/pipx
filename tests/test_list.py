import pytest  # type: ignore

from helpers import mock_legacy_venv, run_pipx_cli
from pipx import constants, util


def test_cli(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert "nothing has been installed with pipx" in captured.out


def test_missing_interpreter(pipx_temp_env, monkeypatch, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])

    _, python_path = util.get_venv_paths(constants.PIPX_LOCAL_VENVS / "pycowsay")
    assert (python_path).is_file()

    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert "package pycowsay has invalid interpreter" not in captured.out

    python_path.unlink()
    assert run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert "package pycowsay has invalid interpreter" in captured.out


def test_list_suffix(pipx_temp_env, monkeypatch, capsys):
    suffix = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])

    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert f"package pycowsay 0.0.0.1 (pycowsay{suffix})," in captured.out


@pytest.mark.parametrize("metadata_version", [None, "0.1"])
def test_list_legacy_venv(pipx_temp_env, monkeypatch, capsys, metadata_version):
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)

    if metadata_version is None:
        assert run_pipx_cli(["list"])
        captured = capsys.readouterr()
        assert "package pycowsay has missing internal pipx metadata" in captured.out
    else:
        assert not run_pipx_cli(["list"])
        captured = capsys.readouterr()
        assert "package pycowsay 0.0.0.1," in captured.out


@pytest.mark.parametrize("metadata_version", ["0.1"])
def test_list_suffix_legacy_venv(pipx_temp_env, monkeypatch, capsys, metadata_version):
    suffix = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])
    mock_legacy_venv(f"pycowsay{suffix}", metadata_version=metadata_version)

    assert not run_pipx_cli(["list"])
    captured = capsys.readouterr()
    assert f"package pycowsay 0.0.0.1 (pycowsay{suffix})," in captured.out
