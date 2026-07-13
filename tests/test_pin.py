import json
from pathlib import Path

import pytest

from helpers import run_pipx_cli
from package_info import PKG
from pipx import paths
from pipx.pipx_metadata_file import PipxMetadata


def test_pin(pipx_temp_env: None, caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["pin", "pycowsay"])
    assert not run_pipx_cli(["upgrade", "pycowsay"])

    assert "Not upgrading pinned package pycowsay" in caplog.text


def test_pin_survives_main_package_extra_injection(pipx_temp_env: None, root: Path) -> None:
    package = root / "testdata/test_package_specifier/local_extras"
    assert not run_pipx_cli(["install", str(package)])
    assert not run_pipx_cli(["pin", "repeatme"])

    assert not run_pipx_cli(["inject", "repeatme", f"{package}[cow]"])

    assert PipxMetadata(paths.ctx.venvs / "repeatme").main_package.pinned


def test_pin_json(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["pin", "pycowsay", "--json"])

    captured = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": "pin",
            "data": {
                "failures": [],
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
            "pipx_result_version": "0.1",
            "status": "success",
        },
        "",
    )


def test_pin_json_reports_missing(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["pin", "missing", "--json"])

    captured = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": "pin",
            "data": {
                "failures": [{"environment": "missing", "error": "pipx does not manage package missing"}],
                "packages": [],
                "skipped": [],
            },
            "pipx_result_version": "0.1",
            "status": "error",
        },
        "",
    )


def test_pin_quiet(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "black"])
    capsys.readouterr()

    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only", "--quiet"])

    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")


def test_pin_json_reports_already_pinned_injected(
    pinned_injected_environment: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only", "--json"])

    assert json.loads(capsys.readouterr().out)["data"] == {
        "failures": [],
        "packages": [],
        "skipped": [{"environment": "pycowsay", "package": "black", "reason": "already-pinned"}],
    }


def test_pin_json_pins_main_after_injected(
    pinned_injected_environment: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["pin", "pycowsay", "--json"])

    assert json.loads(capsys.readouterr().out)["data"] == {
        "failures": [],
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
def pinned_injected_environment(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", "black"])
    assert not run_pipx_cli(["pin", "pycowsay", "--injected-only"])
    capsys.readouterr()


def test_pin_with_suffix(pipx_temp_env: None, caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", PKG["black"]["spec"], "--suffix", "@1"])
    assert not run_pipx_cli(["pin", "black@1"])
    assert not run_pipx_cli(["upgrade", "black@1"])

    assert "Not upgrading pinned package black@1" in caplog.text


def test_pin_warning(pipx_temp_env: None, caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", PKG["nox"]["spec"]])
    assert not run_pipx_cli(["pin", "nox"])
    assert not run_pipx_cli(["pin", "nox"])

    assert "pipx already pins package nox 😴" in caplog.text


def test_pin_not_installed_package(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["pin", "abc"])

    captured = capsys.readouterr()
    assert "pipx does not manage package abc" in captured.err


def test_pin_injected_packages_only(
    pipx_temp_env: None,
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


def test_pin_injected_packages_only_when_main_package_pinned(
    pipx_temp_env: None,
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


def test_pin_injected_packages_with_skip(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["install", "black"])
    assert not run_pipx_cli(["inject", "black", PKG["pylint"]["spec"], PKG["isort"]["spec"]])

    _ = capsys.readouterr()

    assert not run_pipx_cli(["pin", "black", "--injected-only", "--skip", "isort"])

    captured = capsys.readouterr()

    assert "pylint" in captured.out
    assert "isort" not in captured.out
