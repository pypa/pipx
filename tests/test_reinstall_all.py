import importlib
import sys

import pytest

from helpers import PIPX_METADATA_LEGACY_VERSIONS, mock_legacy_venv, run_pipx_cli
from pipx import paths, shared_libs


def test_reinstall_all(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["reinstall-all", "--python", sys.executable])


def test_reinstall_all_none(pipx_temp_env, capsys):
    assert not run_pipx_cli(["reinstall-all"])
    captured = capsys.readouterr()
    assert "No packages reinstalled after running 'pipx reinstall-all'" in captured.out


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


def test_reinstall_all_restores_package_after_keyboard_interrupt(pipx_temp_env, monkeypatch, capsys):
    reinstall_module = importlib.import_module("pipx.commands.reinstall")

    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    venv_dir = paths.ctx.venvs / "pycowsay"
    metadata_before = (venv_dir / "pipx_metadata.json").read_text()

    def interrupting_install(replacement_venv_dir, *args, **kwargs):
        assert not venv_dir.exists()
        replacement_venv_dir.mkdir()
        (replacement_venv_dir / "partial-install").write_text("new")
        raise KeyboardInterrupt

    monkeypatch.setattr(reinstall_module, "install", interrupting_install)

    assert run_pipx_cli(["reinstall-all", "--python", sys.executable])
    captured = capsys.readouterr()

    assert "Reinstall failed; restored pycowsay." in captured.err
    assert venv_dir.exists()
    assert (venv_dir / "pipx_metadata.json").read_text() == metadata_before
    assert not (venv_dir / "partial-install").exists()
    assert not any(path.name.endswith("-pipx-reinstall") for path in paths.ctx.venvs.iterdir())
