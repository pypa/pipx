import sys

import pytest  # type: ignore[import-not-found]

from helpers import PIPX_METADATA_LEGACY_VERSIONS, mock_legacy_venv, run_pipx_cli, skip_if_windows


def test_reinstall(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])


@skip_if_windows
def test_reinstall_global(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "--global", "pycowsay"])
    assert not run_pipx_cli(["reinstall", "--global", "--python", sys.executable, "pycowsay"])


def test_reinstall_nonexistent(pipx_temp_env, capsys):
    assert run_pipx_cli(["reinstall", "--python", sys.executable, "nonexistent"])
    assert "Nothing to reinstall for nonexistent" in capsys.readouterr().out


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
def test_reinstall_legacy_venv(pipx_temp_env, capsys, metadata_version):
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])


def test_reinstall_suffix(pipx_temp_env, capsys):
    suffix = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, f"pycowsay{suffix}"])


@pytest.mark.parametrize("metadata_version", ["0.1"])
def test_reinstall_suffix_legacy_venv(pipx_temp_env, capsys, metadata_version):
    suffix = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])
    mock_legacy_venv(f"pycowsay{suffix}", metadata_version=metadata_version)

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, f"pycowsay{suffix}"])


def test_reinstall_specifier(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pylint==3.0.4"])

    # clear capsys before reinstall
    captured = capsys.readouterr()

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pylint"])
    captured = capsys.readouterr()
    assert "installed package pylint 3.0.4" in captured.out


def test_reinstall_with_path(pipx_temp_env, capsys, tmp_path):
    path = tmp_path / "some" / "path"

    assert run_pipx_cli(["reinstall", str(path)])
    captured = capsys.readouterr()

    assert "Expected the name of an installed package" in captured.err.replace("\n", " ")

    assert run_pipx_cli(["reinstall", str(path.resolve())])
    captured = capsys.readouterr()

    assert "Expected the name of an installed package" in captured.err.replace("\n", " ")
