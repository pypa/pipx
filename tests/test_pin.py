from helpers import run_pipx_cli
from package_info import PKG


def test_pin(monkeypatch, capsys, pipx_temp_env):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["pin", "pycowsay"])
    assert run_pipx_cli(["upgrade", "pycowsay"])

    captured = capsys.readouterr()
    assert "Not upgrading pinned package pycowsay" in captured.err


def test_pin_with_suffix(monkeypatch, capsys, pipx_temp_env):
    assert not run_pipx_cli(["install", PKG["black"]["spec"], "--suffix", "@1"])
    assert not run_pipx_cli(["pin", "black@1"])
    assert run_pipx_cli(["upgrade", "black@1"])

    captured = capsys.readouterr()
    assert "Not upgrading pinned package black@1" in captured.err


def test_unpin(monkeypatch, capsys, pipx_temp_env):
    assert not run_pipx_cli(["install", PKG["nox"]["spec"]])
    assert not run_pipx_cli(["pin", "nox"])
    assert run_pipx_cli(["upgrade", "nox"])

    captured = capsys.readouterr()
    assert "Not upgrading pinned package nox" in captured.err

    assert not run_pipx_cli(["unpin", "nox"])
    assert not run_pipx_cli(["upgrade", "nox"])

    captured = capsys.readouterr()
    assert "nox is already at latest version" in captured.out


def test_pin_and_unpin_warning(monkeypatch, capsys, pipx_temp_env, caplog):
    assert not run_pipx_cli(["install", PKG["nox"]["spec"]])
    assert not run_pipx_cli(["pin", "nox"])
    assert not run_pipx_cli(["pin", "nox"])

    assert "Package nox already pinned 😴" in caplog.text

    assert not run_pipx_cli(["unpin", "nox"])
    assert not run_pipx_cli(["unpin", "nox"])

    assert "Package nox not pinned 😴" in caplog.text


def test_pin_not_installed_package(monkeypatch, capsys, pipx_temp_env):
    assert run_pipx_cli(["pin", "abc"])

    captured = capsys.readouterr()
    assert "Package abc is not installed" in captured.err


def test_unpin_not_installed_package(monkeypatch, capsys, pipx_temp_env):
    assert run_pipx_cli(["unpin", "pkg"])

    captured = capsys.readouterr()
    assert "Package pkg is not installed" in captured.err
