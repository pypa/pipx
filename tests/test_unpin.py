import json
from pathlib import Path

import pytest

from helpers import run_pipx_cli
from package_info import PKG
from pipx import paths


def test_unpin(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["nox"]["spec"]])
    assert not run_pipx_cli(["pin", "nox"])

    assert not run_pipx_cli(["unpin", "nox"])
    assert not run_pipx_cli(["upgrade", "nox"])

    captured = capsys.readouterr()
    assert "nox is already at latest version" in captured.out


def test_unpin_json(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["pin", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["unpin", "pycowsay", "--output", "json"])

    captured = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["unpin"],
            "data": {
                "packages": [
                    {
                        "environment": "pycowsay",
                        "injected": False,
                        "location": str(paths.ctx.venvs / "pycowsay"),
                        "package": "pycowsay",
                        "status": "unpinned",
                        "version": "0.0.0.2",
                    }
                ],
                "skipped": [],
            },
            "pipx_result_version": "1",
            "errors": [],
            "exit_code": 0,
            "status": "success",
        },
        "",
    )


def test_unpin_quiet(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["pin", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["unpin", "pycowsay", "--quiet"])

    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")


def test_unpin_with_suffix(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["black"]["spec"], "--suffix", "@1"])
    assert not run_pipx_cli(["pin", "black@1"])
    assert not run_pipx_cli(["unpin", "black@1"])

    captured = capsys.readouterr()
    assert "pipx unpinned 1 package in venv black@1" in captured.out

    assert not run_pipx_cli(["upgrade", "black@1"])

    captured = capsys.readouterr()
    assert "upgraded package black@1 from 22.8.0 to 22.10.0" in captured.out


def test_unpin_warning(pipx_temp_env: None, caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", PKG["nox"]["spec"]])
    assert not run_pipx_cli(["pin", "nox"])
    assert not run_pipx_cli(["unpin", "nox"])
    assert not run_pipx_cli(["unpin", "nox"])

    assert "pipx found no pinned packages in venv nox" in caplog.text


def test_unpin_not_installed_package(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["unpin", "abc"])

    captured = capsys.readouterr()
    assert "pipx does not manage package abc" in captured.err


def test_unpin_injected_packages(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "black"])
    assert not run_pipx_cli(["inject", "black", "nox", "pylint"])
    assert not run_pipx_cli(["pin", "black"])
    assert not run_pipx_cli(["unpin", "black"])

    captured = capsys.readouterr()
    assert "pipx unpinned 3 packages in venv black" in captured.out


def test_unpin_reports_only_changed_packages(
    pipx_temp_env: None,
    empty_project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", str(empty_project)])
    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only"])
    capsys.readouterr()

    assert not run_pipx_cli(["unpin", "pycowsay"])
    output = capsys.readouterr().out
    assert "pipx unpinned 1 package in venv pycowsay" in output
    assert "  - empty-project" in output
    assert "  - pycowsay" not in output
