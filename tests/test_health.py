from __future__ import annotations

import importlib
import json
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, Final

import pytest

from helpers import remove_venv_interpreter, run_pipx_cli
from pipx import paths, util

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType

    from pytest_mock import MockerFixture

_HEALTH_MODULE: Final[ModuleType] = importlib.import_module("pipx.commands.health")


@pytest.fixture
def installed_pycowsay(
    pipx_temp_env: None,  # noqa: ARG001  # required so the temp env is active while pycowsay is installed
    capsys: pytest.CaptureFixture[str],
) -> Path:
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
@pytest.mark.usefixtures("pipx_temp_env")
def test_environment_maintenance_no_packages(
    capsys: pytest.CaptureFixture[str],
    command: str,
    message: str,
) -> None:
    assert run_pipx_cli([command]) == 0

    assert capsys.readouterr().out == message


def test_health_json(installed_pycowsay: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["health", "pycowsay", "--output", "json"]) == 0

    assert json.loads(capsys.readouterr().out) == {
        "command": ["health"],
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
        "pipx_result_version": "1",
        "errors": [],
        "exit_code": 0,
        "status": "success",
    }


@pytest.mark.usefixtures("installed_pycowsay")
def test_health_deduplicates_repeated_package(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["health", "pycowsay", "PyCowSay", "--output", "json"]) == 0

    environments = json.loads(capsys.readouterr().out)["data"]["environments"]
    assert [environment["environment"] for environment in environments] == ["pycowsay"]


@pytest.mark.usefixtures("pipx_temp_env")
def test_repair_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["repair", "--output", "json"]) == 0

    assert json.loads(capsys.readouterr().out) == {
        "command": ["repair"],
        "data": {"repaired": [], "skipped": []},
        "pipx_result_version": "1",
        "errors": [],
        "exit_code": 0,
        "status": "success",
    }


def test_health_reports_broken_interpreter(installed_pycowsay: Path, capsys: pytest.CaptureFixture[str]) -> None:
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
    capsys: pytest.CaptureFixture[str],
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
@pytest.mark.usefixtures("pipx_temp_env")
def test_environment_maintenance_reports_unmanaged_package(
    capsys: pytest.CaptureFixture[str],
    command: str,
    output: tuple[str, str],
) -> None:
    assert run_pipx_cli([command, "missing"]) == 1

    captured = capsys.readouterr()
    assert (captured.out, captured.err) == output


@pytest.mark.usefixtures("installed_pycowsay")
def test_repair_rebuilds_broken_interpreter(capsys: pytest.CaptureFixture[str]) -> None:
    remove_venv_interpreter("pycowsay")

    assert run_pipx_cli(["repair", "--python", sys.executable]) == 0
    capsys.readouterr()

    assert run_pipx_cli(["health", "pycowsay"]) == 0
    assert "pycowsay: healthy" in capsys.readouterr().out


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not on PATH")
@pytest.mark.usefixtures("pipx_temp_env")
def test_repair_preserves_uv_backend(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["install", "--backend", "uv", "--python", sys.executable, "pycowsay"]) == 0
    remove_venv_interpreter("pycowsay")
    capsys.readouterr()

    assert run_pipx_cli(["repair", "--python", sys.executable, "pycowsay"]) == 0
    capsys.readouterr()
    assert run_pipx_cli(["list", "--json"]) == 0

    assert json.loads(capsys.readouterr().out)["venvs"]["pycowsay"]["metadata"]["backend"] == "uv"


@pytest.mark.usefixtures("installed_pycowsay")
def test_repair_skips_healthy_interpreter(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["repair", "pycowsay"]) == 0

    assert capsys.readouterr().out == "pycowsay: healthy\n"


@pytest.mark.usefixtures("installed_pycowsay")
def test_repair_respects_pin(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["pin", "pycowsay"]) == 0
    remove_venv_interpreter("pycowsay")
    capsys.readouterr()

    assert run_pipx_cli(["repair", "pycowsay"]) == 1

    assert "is pinned. Run `pipx unpin pycowsay` to unpin it first." in capsys.readouterr().err.replace("\n", " ")


@pytest.mark.usefixtures("installed_pycowsay")
def test_repair_verifies_rebuilt_interpreter(
    capsys: pytest.CaptureFixture[str],
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


@pytest.mark.usefixtures("installed_pycowsay")
def test_repair_json_stays_pure_when_it_reinstalls(capsys: pytest.CaptureFixture[str]) -> None:
    remove_venv_interpreter("pycowsay")

    assert not run_pipx_cli(["repair", "--python", sys.executable, "--output", "json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)  # the internal reinstall must not print human text before this
    assert (document["command"], document["status"], captured.err) == (["repair"], "success", "")
