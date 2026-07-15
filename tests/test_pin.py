from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from helpers import run_pipx_cli
from package_info import PKG
from pipx import paths
from pipx.pipx_metadata_file import PipxMetadata

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin(caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["pin", "pycowsay"])
    assert not run_pipx_cli(["upgrade", "pycowsay"])

    assert "Not upgrading pinned package pycowsay" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_survives_main_package_extra_injection(local_extras_project: Path) -> None:
    assert not run_pipx_cli(["install", str(local_extras_project)])
    assert not run_pipx_cli(["pin", "repeatme"])

    assert not run_pipx_cli(["inject", "repeatme", f"{local_extras_project}[cow]"])

    assert PipxMetadata(paths.ctx.venvs / "repeatme").main_package.pinned


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["pin", "pycowsay", "--output", "json"])

    captured = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["pin"],
            "data": {
                "packages": [
                    {
                        "environment": "pycowsay",
                        "injected": False,
                        "location": str(paths.ctx.venvs / "pycowsay"),
                        "package": "pycowsay",
                        "status": "pinned",
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
def test_pin_json_reports_missing(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["pin", "missing", "--output", "json"])

    captured = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["pin"],
            "data": {"packages": [], "skipped": []},
            "errors": [
                {
                    "code": "package_pin_failed",
                    "environment": "missing",
                    "message": "pipx does not manage package missing",
                    "package": None,
                }
            ],
            "exit_code": 1,
            "pipx_result_version": "1",
            "status": "error",
        },
        "",
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_quiet(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "black"])
    capsys.readouterr()

    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only", "--quiet"])

    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")


@pytest.mark.usefixtures("pinned_injected_environment")
def test_pin_json_reports_already_pinned_injected(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only", "--output", "json"])

    assert json.loads(capsys.readouterr().out)["data"] == {
        "packages": [],
        "skipped": [{"environment": "pycowsay", "package": "black", "reason": "already-pinned"}],
    }


@pytest.mark.usefixtures("pinned_injected_environment")
def test_pin_json_pins_main_after_injected(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["pin", "pycowsay", "--output", "json"])

    assert json.loads(capsys.readouterr().out)["data"] == {
        "packages": [
            {
                "environment": "pycowsay",
                "injected": False,
                "location": str(paths.ctx.venvs / "pycowsay"),
                "package": "pycowsay",
                "status": "pinned",
                "version": "0.0.0.2",
            }
        ],
        "skipped": [{"environment": "pycowsay", "package": "black", "reason": "already-pinned"}],
    }


@pytest.fixture
def pinned_injected_environment(
    pipx_temp_env: None,  # noqa: ARG001  # required so the temp env is active while the environment is built
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "black"])
    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only"])
    capsys.readouterr()


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_with_suffix(caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", PKG["black"]["spec"], "--suffix", "@1"])
    assert not run_pipx_cli(["pin", "black@1"])
    assert not run_pipx_cli(["upgrade", "black@1"])

    assert "Not upgrading pinned package black@1" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_warning(caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", PKG["nox"]["spec"]])
    assert not run_pipx_cli(["pin", "nox"])
    assert not run_pipx_cli(["pin", "nox"])

    assert "pipx already pins package nox 😴" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_not_installed_package(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["pin", "abc"])

    captured = capsys.readouterr()
    assert "pipx does not manage package abc" in captured.err


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_injected_packages_only(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "black", PKG["pylint"]["spec"]])

    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only"])

    captured = capsys.readouterr()

    assert "pipx pinned 2 packages in venv pycowsay" in captured.out
    assert "black" in captured.out
    assert "pylint" in captured.out

    assert not run_pipx_cli(["upgrade", "pycowsay", "--include-injected"])

    assert "Not upgrading pinned package black in venv pycowsay" in caplog.text
    assert "Not upgrading pinned package pylint in venv pycowsay" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_injected_packages_only_when_main_package_pinned(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["pin", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "black", PKG["pylint"]["spec"]])

    _ = capsys.readouterr()
    caplog.clear()

    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only"])

    captured = capsys.readouterr()

    assert "pipx pinned 2 packages in venv pycowsay" in captured.out
    assert "black" in captured.out
    assert "pylint" in captured.out
    assert "pipx already pins package pycowsay" not in caplog.text

    assert not run_pipx_cli(["upgrade", "pycowsay", "--include-injected"])

    assert "Not upgrading pinned package pycowsay" in caplog.text
    assert "Not upgrading pinned package black in venv pycowsay" in caplog.text
    assert "Not upgrading pinned package pylint in venv pycowsay" in caplog.text


@pytest.mark.usefixtures("pipx_temp_env")
def test_pin_injected_packages_with_skip(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["install", "black"])
    assert not run_pipx_cli(["inject", "black", PKG["pylint"]["spec"], PKG["isort"]["spec"]])

    _ = capsys.readouterr()

    assert not run_pipx_cli(["pin", "black", "--injected-only", "--skip", "isort"])

    captured = capsys.readouterr()

    assert "pylint" in captured.out
    assert "isort" not in captured.out
