from helpers import run_pipx_cli
from package_info import PKG


def test_unpin(monkeypatch, capsys, pipx_temp_env):
    assert not run_pipx_cli(["install", PKG["nox"]["spec"]])
    assert not run_pipx_cli(["pin", "nox"])
    assert not run_pipx_cli(["upgrade", "nox"])

    captured = capsys.readouterr()
    assert "Not upgrading pinned package nox" in captured.out

    assert not run_pipx_cli(["unpin", "nox"])
    assert not run_pipx_cli(["upgrade", "nox"])

    captured = capsys.readouterr()
    assert "nox is already at latest version" in captured.out


def test_unpin_with_suffix(monkeypatch, capsys, pipx_temp_env):
    assert not run_pipx_cli(["install", PKG["black"]["spec"], "--suffix", "@1"])
    assert not run_pipx_cli(["pin", "black@1"])
    assert not run_pipx_cli(["unpin", "black@1"])

    captured = capsys.readouterr()
    assert "Unpinned 1 packages in venv black@1" in captured.out


def test_unpin_warning(monkeypatch, capsys, pipx_temp_env, caplog):
    assert not run_pipx_cli(["install", PKG["nox"]["spec"]])
    assert not run_pipx_cli(["pin", "nox"])
    assert not run_pipx_cli(["unpin", "nox"])
    assert not run_pipx_cli(["unpin", "nox"])

    assert "No packages to unpin in venv nox" in caplog.text


def test_pin_not_installed_package(monkeypatch, capsys, pipx_temp_env):
    assert run_pipx_cli(["unpin", "abc"])

    captured = capsys.readouterr()
    assert "Package abc is not installed" in captured.err
