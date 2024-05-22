from helpers import run_pipx_cli
from package_info import PKG


def test_pin(capsys, pipx_temp_env, caplog):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["pin", "pycowsay"])
    assert not run_pipx_cli(["upgrade", "pycowsay"])

    assert "Not upgrading pinned package pycowsay" in caplog.text


def test_pin_with_suffix(capsys, pipx_temp_env, caplog):
    assert not run_pipx_cli(["install", PKG["black"]["spec"], "--suffix", "@1"])
    assert not run_pipx_cli(["pin", "black@1"])
    assert not run_pipx_cli(["upgrade", "black@1"])

    assert "Not upgrading pinned package black@1" in caplog.text


def test_pin_warning(capsys, pipx_temp_env, caplog):
    assert not run_pipx_cli(["install", PKG["nox"]["spec"]])
    assert not run_pipx_cli(["pin", "nox"])
    assert not run_pipx_cli(["pin", "nox"])

    assert "Package nox already pinned 😴" in caplog.text


def test_pin_not_installed_package(capsys, pipx_temp_env):
    assert run_pipx_cli(["pin", "abc"])

    captured = capsys.readouterr()
    assert "Package abc is not installed" in captured.err


def test_pin_injected_packages_only(capsys, pipx_temp_env, caplog):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "black", PKG["pylint"]["spec"]])

    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only"])

    captured = capsys.readouterr()

    assert "Pinned 2 packages in venv pycowsay" in captured.out
    assert "black" in captured.out
    assert "pylint" in captured.out

    assert not run_pipx_cli(["upgrade", "pycowsay", "--include-injected"])

    assert "Not upgrading pinned package black in venv pycowsay" in caplog.text
    assert "Not upgrading pinned package pylint in venv pycowsay" in caplog.text


def test_pin_injected_packages_with_skip(capsys, pipx_temp_env):
    assert not run_pipx_cli(["install", "black"])
    assert not run_pipx_cli(["inject", "black", PKG["pylint"]["spec"], PKG["isort"]["spec"]])

    _ = capsys.readouterr()

    assert not run_pipx_cli(["pin", "black", "--injected-only", "--skip", "isort"])

    captured = capsys.readouterr()

    assert "pylint" in captured.out
    assert "isort" not in captured.out
