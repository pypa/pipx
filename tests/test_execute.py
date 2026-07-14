from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from helpers import app_name, run_pipx_cli
from pipx import paths
from pipx.util import get_venv_paths

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    ("setup_commands", "environment_name", "application"),
    [
        pytest.param([["install", "pylint==3.0.4"]], "pylint", "isort", id="dependency"),
        pytest.param(
            [["install", "pycowsay"], ["inject", "pycowsay", "black"]],
            "pycowsay",
            "black",
            id="injected",
        ),
    ],
)
def test_execute_runs_recorded_app(
    pipx_temp_env: None,
    mocker: MockerFixture,
    setup_commands: list[list[str]],
    environment_name: str,
    application: str,
) -> None:
    for setup_command in setup_commands:
        assert not run_pipx_cli(setup_command)
    boundary: Final[MagicMock] = mocker.patch.object(
        importlib.import_module("pipx.commands.execute"),
        "exec_app",
        autospec=True,
        side_effect=RuntimeError("exec"),
    )

    with pytest.raises(RuntimeError, match="exec"):
        run_pipx_cli(["exec", environment_name, application, "--version"])

    command: Final[list[str | Path]] = boundary.call_args.args[0]
    environment: Final[dict[str, str]] = boundary.call_args.kwargs["env"]
    venv_dir: Final[Path] = paths.ctx.venvs / environment_name
    bin_dir: Final[Path] = get_venv_paths(venv_dir)[0]
    assert (
        Path(command[0]),
        command[1:],
        environment["VIRTUAL_ENV"],
        environment["PATH"].split(os.pathsep)[0],
    ) == (bin_dir / app_name(application), ["--version"], str(venv_dir), str(bin_dir))


def test_execute_rejects_unknown_app(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert run_pipx_cli(["exec", "pycowsay", "missing"]) == 1

    assert " ".join(capsys.readouterr().err.split()) == (
        "Application 'missing' was not found in environment 'pycowsay'. Available applications: pycowsay"
    )


def test_execute_rejects_unknown_environment(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["exec", "missing", "app"]) == 1

    assert capsys.readouterr().err == "pipx does not manage environment 'missing'.\n"


def test_execute_rejects_missing_recorded_app(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    venv_dir: Final[Path] = paths.ctx.venvs / "pycowsay"
    app_path: Final[Path] = get_venv_paths(venv_dir)[0] / app_name("pycowsay")
    app_path.unlink()
    capsys.readouterr()

    assert run_pipx_cli(["exec", "pycowsay", "pycowsay"]) == 1

    assert " ".join(capsys.readouterr().err.split()) == (
        f"Application 'pycowsay' is missing from environment 'pycowsay' at {app_path}. "
        "Reinstall it with `pipx reinstall pycowsay`."
    )
