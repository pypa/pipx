from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from helpers import run_pipx_cli
from package_info import PKG
from pipx import paths

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.usefixtures("pipx_temp_env")
def test_unpin(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["nox"]["spec"]])
    assert not run_pipx_cli(["pin", "nox"])

    assert not run_pipx_cli(["unpin", "nox"])
    assert not run_pipx_cli(["upgrade", "nox"])

    captured = capsys.readouterr()
    assert "nox is already at latest version" in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_unpin_json(capsys: pytest.CaptureFixture[str]) -> None:
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


@pytest.mark.usefixtures("pipx_temp_env")
def test_unpin_quiet(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["pin", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["unpin", "pycowsay", "--quiet"])

    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")


@pytest.mark.usefixtures("pipx_temp_env")
def test_unpin_with_suffix(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["black"]["spec"], "--suffix", "@1"])
    assert not run_pipx_cli(["pin", "black@1"])
    assert not run_pipx_cli(["unpin", "black@1"])

    captured = capsys.readouterr()
    assert "pipx unpinned 1 package in venv black@1" in captured.out

    assert not run_pipx_cli(["upgrade", "black@1"])

    captured = capsys.readouterr()
    assert "upgraded package black@1 from 22.8.0 to 22.10.0" in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_unpin_warning(caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", PKG["nox"]["spec"]])
    assert not run_pipx_cli(["pin", "nox"])
    assert not run_pipx_cli(["unpin", "nox"])
    assert not run_pipx_cli(["unpin", "nox"])

    assert "pipx found no pinned packages in venv nox" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env")
def test_unpin_not_installed_package(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["unpin", "abc"])

    captured = capsys.readouterr()
    assert "pipx does not manage package abc" in captured.err


@pytest.mark.usefixtures("pipx_temp_env")
def test_unpin_injected_packages(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "black"])
    assert not run_pipx_cli(["inject", "black", "nox", "pylint"])
    assert not run_pipx_cli(["pin", "black"])
    assert not run_pipx_cli(["unpin", "black"])

    captured = capsys.readouterr()
    assert "pipx unpinned 3 packages in venv black" in captured.out


@pytest.mark.usefixtures("pipx_temp_env")
def test_unpin_reports_only_changed_packages(
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
