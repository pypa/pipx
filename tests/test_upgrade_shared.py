import subprocess

import pytest  # type: ignore[import-not-found]

from helpers import run_pipx_cli


@pytest.fixture
def shared_libs(pipx_ultra_temp_env):
    # local import to get the shared_libs object patched by fixtures
    from pipx.shared_libs import shared_libs as _shared_libs

    yield _shared_libs


def test_upgrade_shared(shared_libs, capsys, caplog):
    assert shared_libs.has_been_updated_this_run is False
    assert shared_libs.is_valid is False
    assert run_pipx_cli(["upgrade-shared", "-v"]) == 0
    captured = capsys.readouterr()
    assert "creating shared libraries" in captured.err
    assert "upgrading shared libraries" in captured.err
    assert "Upgrading shared libraries in" in caplog.text
    assert "Already upgraded libraries in" not in caplog.text
    assert shared_libs.has_been_updated_this_run is True
    assert shared_libs.is_valid is True
    shared_libs.has_been_updated_this_run = False
    assert run_pipx_cli(["upgrade-shared", "-v"]) == 0
    captured = capsys.readouterr()
    assert "creating shared libraries" not in captured.err
    assert "upgrading shared libraries" in captured.err
    assert "Upgrading shared libraries in" in caplog.text
    assert "Already upgraded libraries in" not in caplog.text
    assert shared_libs.has_been_updated_this_run is True
    assert run_pipx_cli(["upgrade-shared", "-v"]) == 0
    assert "Already upgraded libraries in" in caplog.text


def test_upgrade_shared_pip_args(shared_libs, capsys, caplog):
    assert shared_libs.has_been_updated_this_run is False
    assert shared_libs.is_valid is False
    assert run_pipx_cli(["upgrade-shared", "-v", "--pip-args='--no-index'"]) == 1
    captured = capsys.readouterr()
    assert "creating shared libraries" in captured.err
    assert "upgrading shared libraries" in captured.err
    assert "Upgrading shared libraries in" in caplog.text
    assert "Already upgraded libraries in" not in caplog.text
    assert shared_libs.has_been_updated_this_run is False
    assert shared_libs.is_valid is True


def test_upgrade_shared_pin_pip(shared_libs):
    def pip_version():
        cmd = "from importlib.metadata import version; print(version('pip'))"
        ret = subprocess.run([shared_libs.python_path, "-c", cmd], check=True, capture_output=True, text=True)
        return ret.stdout.strip()

    assert shared_libs.has_been_updated_this_run is False
    assert shared_libs.is_valid is False
    assert run_pipx_cli(["upgrade-shared", "-v", "--pip-args=pip==24.0"]) == 0
    assert shared_libs.is_valid is True
    assert pip_version() == "24.0"
    shared_libs.has_been_updated_this_run = False  # reset for next run
    assert run_pipx_cli(["upgrade-shared", "-v", "--pip-args=pip==23.3.2"]) == 0
    assert shared_libs.is_valid is True
    assert pip_version() == "23.3.2"
