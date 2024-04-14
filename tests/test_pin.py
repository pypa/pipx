from helpers import run_pipx_cli
from package_info import PKG


def test_pin(monkeypatch, capsys, pipx_temp_env):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["pin", "pycowsay"])
    assert not run_pipx_cli(["upgrade", "pycowsay"])

    captured = capsys.readouterr()
    assert "Not upgrading pinned package pycowsay" in captured.out


def test_pin_with_suffix(monkeypatch, capsys, pipx_temp_env):
    assert not run_pipx_cli(["install", PKG["black"]["spec"], "--suffix", "@1"])
    assert not run_pipx_cli(["pin", "black@1"])
    assert not run_pipx_cli(["upgrade", "black@1"])

    captured = capsys.readouterr()
    assert "Not upgrading pinned package black@1" in captured.out

    assert not run_pipx_cli(["unpin", "black@1"])

    captured = capsys.readouterr()
    assert "Unpinned 1 packages in venv black@1" in captured.out


def test_pin_warning(monkeypatch, capsys, pipx_temp_env, caplog):
    assert not run_pipx_cli(["install", PKG["nox"]["spec"]])
    assert not run_pipx_cli(["pin", "nox"])
    assert not run_pipx_cli(["pin", "nox"])

    assert "Package nox already pinned 😴" in caplog.text


def test_pin_not_installed_package(monkeypatch, capsys, pipx_temp_env):
    assert run_pipx_cli(["pin", "abc"])

    captured = capsys.readouterr()
    assert "Package abc is not installed" in captured.err


def test_unpin_not_installed_package(monkeypatch, capsys, pipx_temp_env):
    assert run_pipx_cli(["unpin", "pkg"])

    captured = capsys.readouterr()
    assert "Package pkg is not installed" in captured.err


def test_pin_unpin_injected_packages_only(monkeypatch, capsys, pipx_temp_env):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "black", PKG["pylint"]["spec"]])

    assert not run_pipx_cli(["pin", "pycowsay", "--injected-packages-only"])

    captured = capsys.readouterr()

    assert "Pinned 2 packages in venv pycowsay" in captured.out
    assert "black" in captured.out
    assert "pylint" in captured.out

    assert not run_pipx_cli(["unpin", "pycowsay"])

    captured = capsys.readouterr()

    assert "Unpinned 2 packages in venv pycowsay" in captured.out
    assert "black" in captured.out
    assert "pylint" in captured.out


def test_pin_injected_packages_with_skip(monkeypatch, capsys, pipx_temp_env):
    assert not run_pipx_cli(["install", "black"])
    assert not run_pipx_cli(["inject", "black", PKG["pylint"]["spec"], PKG["isort"]["spec"]])

    assert not run_pipx_cli(["pin", "black", "--injected-packages-only", "--skip", "isort"])

    captured = capsys.readouterr()

    assert "pylint" in captured.out
    assert "isort" not in captured.out