from helpers import run_pipx_cli


def test_upgrade_shared(pipx_ultra_temp_env, capsys, caplog, monkeypatch):
    from pipx.shared_libs import shared_libs

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


def test_upgrade_shared_pip_args(pipx_ultra_temp_env, capsys, caplog, monkeypatch):
    from pipx.shared_libs import shared_libs

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
