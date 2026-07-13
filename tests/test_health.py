import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Final

import pytest
from pytest import CaptureFixture
from pytest_mock import MockerFixture

from helpers import remove_venv_interpreter, run_pipx_cli
from pipx import paths, util

_HEALTH_MODULE: Final[ModuleType] = importlib.import_module("pipx.commands.health")


@pytest.fixture
def installed_pycowsay(pipx_temp_env: None, capsys: CaptureFixture[str]) -> Path:
    assert run_pipx_cli(["install", "pycowsay"]) == 0
    capsys.readouterr()
    return paths.ctx.venvs / "pycowsay"


@pytest.mark.parametrize(
    ("command", "message"),
    [
        pytest.param("health", "pipx manages no packages.\n", id="health"),
        pytest.param("repair", "pipx found no environments to repair.\n", id="repair"),
    ],
)
def test_environment_maintenance_no_packages(
    pipx_temp_env: None,
    capsys: CaptureFixture[str],
    command: str,
    message: str,
) -> None:
    assert run_pipx_cli([command]) == 0

    assert capsys.readouterr().out == message


def test_health_json(installed_pycowsay: Path, capsys: CaptureFixture[str]) -> None:
    assert run_pipx_cli(["health", "pycowsay", "--json"]) == 0

    assert json.loads(capsys.readouterr().out) == {
        "command": "health",
        "data": {
            "environments": [
                {
                    "environment": "pycowsay",
                    "error": None,
                    "interpreter": str(util.get_venv_paths(installed_pycowsay)[1]),
                    "status": "healthy",
                }
            ]
        },
        "pipx_result_version": "0.1",
        "status": "success",
    }


def test_health_reports_broken_interpreter(installed_pycowsay: Path, capsys: CaptureFixture[str]) -> None:
    remove_venv_interpreter("pycowsay")

    assert run_pipx_cli(["health"]) == 1

    assert capsys.readouterr().out == (
        f"pycowsay: interpreter is missing at {util.get_venv_paths(installed_pycowsay)[1]}\n"
    )


@pytest.mark.parametrize(
    ("failure", "error"),
    [
        pytest.param(
            subprocess.CompletedProcess(["python", "--version"], 7, "", "failure"),
            "interpreter exited with status 7",
            id="exit-status",
        ),
        pytest.param(PermissionError("denied"), "interpreter could not start: denied", id="start-error"),
    ],
)
def test_health_reports_interpreter_failure(
    installed_pycowsay: Path,
    capsys: CaptureFixture[str],
    mocker: MockerFixture,
    failure: subprocess.CompletedProcess[str] | OSError,
    error: str,
) -> None:
    if isinstance(failure, OSError):
        mocker.patch.object(_HEALTH_MODULE, "run_subprocess", autospec=True, side_effect=failure)
    else:
        mocker.patch.object(_HEALTH_MODULE, "run_subprocess", autospec=True, return_value=failure)

    assert run_pipx_cli(["health", "pycowsay"]) == 1

    assert capsys.readouterr().out == (f"pycowsay: {error} at {util.get_venv_paths(installed_pycowsay)[1]}\n")


@pytest.mark.parametrize(
    ("command", "output"),
    [
        pytest.param("health", ("missing: pipx does not manage this environment\n", ""), id="health"),
        pytest.param("repair", ("", "missing: pipx does not manage this environment\n"), id="repair"),
    ],
)
def test_environment_maintenance_reports_unmanaged_package(
    pipx_temp_env: None,
    capsys: CaptureFixture[str],
    command: str,
    output: tuple[str, str],
) -> None:
    assert run_pipx_cli([command, "missing"]) == 1

    captured = capsys.readouterr()
    assert (captured.out, captured.err) == output


def test_repair_rebuilds_broken_interpreter(installed_pycowsay: Path, capsys: CaptureFixture[str]) -> None:
    remove_venv_interpreter("pycowsay")

    assert run_pipx_cli(["repair", "--python", sys.executable]) == 0
    capsys.readouterr()

    assert run_pipx_cli(["health", "pycowsay"]) == 0
    assert "pycowsay: healthy" in capsys.readouterr().out


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not on PATH")
def test_repair_preserves_uv_backend(pipx_temp_env: None, capsys: CaptureFixture[str]) -> None:
    assert run_pipx_cli(["install", "--backend", "uv", "--python", sys.executable, "pycowsay"]) == 0
    remove_venv_interpreter("pycowsay")
    capsys.readouterr()

    assert run_pipx_cli(["repair", "--python", sys.executable, "pycowsay"]) == 0
    capsys.readouterr()
    assert run_pipx_cli(["list", "--json"]) == 0

    assert json.loads(capsys.readouterr().out)["venvs"]["pycowsay"]["metadata"]["backend"] == "uv"


def test_repair_skips_healthy_interpreter(installed_pycowsay: Path, capsys: CaptureFixture[str]) -> None:
    assert run_pipx_cli(["repair", "pycowsay"]) == 0

    assert capsys.readouterr().out == "pycowsay: healthy\n"


def test_repair_respects_pin(installed_pycowsay: Path, capsys: CaptureFixture[str]) -> None:
    assert run_pipx_cli(["pin", "pycowsay"]) == 0
    remove_venv_interpreter("pycowsay")
    capsys.readouterr()

    assert run_pipx_cli(["repair", "pycowsay"]) == 1

    assert "is pinned. Run `pipx unpin pycowsay` to unpin it first." in capsys.readouterr().err.replace("\n", " ")


def test_repair_verifies_rebuilt_interpreter(
    installed_pycowsay: Path,
    capsys: CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    remove_venv_interpreter("pycowsay")
    capsys.readouterr()
    mocker.patch.object(
        _HEALTH_MODULE,
        "run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(["python", "--version"], 7, "", "failure"),
    )

    assert run_pipx_cli(["repair", "--python", sys.executable, "pycowsay"]) == 1

    assert "pycowsay: interpreter exited with status 7" in capsys.readouterr().err
