from pathlib import Path

import pytest

from helpers import run_pipx_cli
from package_info import PKG


def test_unpin(capsys, pipx_temp_env, caplog):
    assert not run_pipx_cli(["install", PKG["nox"]["spec"]])
    assert not run_pipx_cli(["pin", "nox"])

    assert not run_pipx_cli(["unpin", "nox"])
    assert not run_pipx_cli(["upgrade", "nox"])

    captured = capsys.readouterr()
    assert "nox is already at latest version" in captured.out


def test_unpin_with_suffix(capsys, pipx_temp_env):
    assert not run_pipx_cli(["install", PKG["black"]["spec"], "--suffix", "@1"])
    assert not run_pipx_cli(["pin", "black@1"])
    assert not run_pipx_cli(["unpin", "black@1"])

    captured = capsys.readouterr()
    assert "Unpinned 1 packages in venv black@1" in captured.out

    assert not run_pipx_cli(["upgrade", "black@1"])

    captured = capsys.readouterr()
    assert "upgraded package black@1 from 22.8.0 to 22.10.0" in captured.out


def test_unpin_warning(capsys, pipx_temp_env, caplog):
    assert not run_pipx_cli(["install", PKG["nox"]["spec"]])
    assert not run_pipx_cli(["pin", "nox"])
    assert not run_pipx_cli(["unpin", "nox"])
    assert not run_pipx_cli(["unpin", "nox"])

    assert "No packages to unpin in venv nox" in caplog.text


def test_unpin_not_installed_package(capsys, pipx_temp_env):
    assert run_pipx_cli(["unpin", "abc"])

    captured = capsys.readouterr()
    assert "Package abc is not installed" in captured.err


def test_unpin_injected_packages(capsys, pipx_temp_env):
    assert not run_pipx_cli(["install", "black"])
    assert not run_pipx_cli(["inject", "black", "nox", "pylint"])
    assert not run_pipx_cli(["pin", "black"])
    assert not run_pipx_cli(["unpin", "black"])

    captured = capsys.readouterr()
    assert "Unpinned 3 packages in venv black" in captured.out


def test_unpin_reports_only_changed_packages(
    pipx_temp_env: None,
    root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", str(root / "testdata/empty_project")])
    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only"])
    capsys.readouterr()

    assert not run_pipx_cli(["unpin", "pycowsay"])
    output = capsys.readouterr().out
    assert "Unpinned 1 packages in venv pycowsay" in output
    assert "  - empty-project" in output
    assert "  - pycowsay" not in output
