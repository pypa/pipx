import json
import sys
from pathlib import Path

import pytest
from pytest import CaptureFixture

from helpers import app_name, mock_legacy_venv, run_pipx_cli
from package_info import PKG
from pipx import paths
from pipx.pipx_metadata_file import PipxMetadata


@pytest.fixture
def installed_pycowsay(pipx_temp_env: None, capsys: CaptureFixture[str]) -> Path:
    assert run_pipx_cli(["install", "pycowsay"]) == 0
    capsys.readouterr()
    return paths.ctx.venvs / "pycowsay"


@pytest.fixture
def unexposed_pycowsay(installed_pycowsay: Path, capsys: CaptureFixture[str]) -> Path:
    assert run_pipx_cli(["unexpose", "pycowsay"]) == 0
    capsys.readouterr()
    return installed_pycowsay


def test_unexpose_hides_resources(installed_pycowsay: Path, capsys: CaptureFixture[str]) -> None:
    assert run_pipx_cli(["unexpose", "pycowsay"]) == 0

    assert not (paths.ctx.bin_dir / app_name("pycowsay")).exists()
    assert not (paths.ctx.man_dir / "man6" / "pycowsay.6").exists()
    assert installed_pycowsay.exists()
    assert PipxMetadata(installed_pycowsay).exposure_enabled is False
    assert capsys.readouterr().out == "pycowsay: unexposed\n"


def test_expose_restores_resources(unexposed_pycowsay: Path, capsys: CaptureFixture[str]) -> None:
    assert run_pipx_cli(["expose", "pycowsay"]) == 0

    assert (paths.ctx.bin_dir / app_name("pycowsay")).exists()
    assert (paths.ctx.man_dir / "man6" / "pycowsay.6").exists()
    assert PipxMetadata(unexposed_pycowsay).exposure_enabled is True
    assert capsys.readouterr().out == "pycowsay: exposed\n"


def test_upgrade_preserves_unexposed_state(pipx_temp_env: None, capsys: CaptureFixture[str]) -> None:
    assert run_pipx_cli(["install", "pylint==3.0.4"]) == 0
    assert run_pipx_cli(["unexpose", "pylint"]) == 0
    venv_dir = paths.ctx.venvs / "pylint"
    previous_version = PipxMetadata(venv_dir).main_package.package_version
    capsys.readouterr()

    assert run_pipx_cli(["upgrade", "pylint"]) == 0
    capsys.readouterr()

    metadata = PipxMetadata(venv_dir)
    assert metadata.main_package.package_version != previous_version
    assert not (paths.ctx.bin_dir / app_name("pylint")).exists()
    assert metadata.exposure_enabled is False


def test_install_upgrade_preserves_unexposed_state(pipx_temp_env: None, capsys: CaptureFixture[str]) -> None:
    assert run_pipx_cli(["install", PKG["black"]["spec"]]) == 0
    assert run_pipx_cli(["unexpose", "black"]) == 0
    capsys.readouterr()

    assert run_pipx_cli(["install", "--upgrade", "black==22.10.0"]) == 0
    output = capsys.readouterr().out

    metadata = PipxMetadata(paths.ctx.venvs / "black")
    assert "upgraded package black from 22.8.0 to 22.10.0" in output
    assert not (paths.ctx.bin_dir / app_name("black")).exists()
    assert metadata.exposure_enabled is False


def test_force_install_preserves_unexposed_state(
    unexposed_pycowsay: Path,
    capsys: CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["install", "--force", "pycowsay"]) == 0
    output = capsys.readouterr().out

    assert "installed package pycowsay" in output
    assert not (paths.ctx.bin_dir / app_name("pycowsay")).exists()
    assert PipxMetadata(unexposed_pycowsay).exposure_enabled is False


def test_reinstall_preserves_unexposed_state(
    unexposed_pycowsay: Path,
    capsys: CaptureFixture[str],
) -> None:
    marker = unexposed_pycowsay / "marker"
    marker.touch()

    assert run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"]) == 0
    capsys.readouterr()

    assert not marker.exists()
    assert not (paths.ctx.bin_dir / app_name("pycowsay")).exists()
    assert PipxMetadata(unexposed_pycowsay).exposure_enabled is False


def test_unexposed_environment_does_not_expose_injected_apps(
    unexposed_pycowsay: Path,
    capsys: CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["inject", "--include-apps", "pycowsay", "pylint"]) == 0
    capsys.readouterr()

    metadata = PipxMetadata(unexposed_pycowsay)
    assert "pylint" in metadata.injected_packages
    assert not (paths.ctx.bin_dir / app_name("pylint")).exists()
    assert metadata.exposure_enabled is False


def test_install_all_preserves_unexposed_state(
    unexposed_pycowsay: Path,
    capsys: CaptureFixture[str],
    tmp_path: Path,
) -> None:
    assert run_pipx_cli(["list", "--json"]) == 0
    spec_path = tmp_path / "pipx.json"
    spec_path.write_text(capsys.readouterr().out, encoding="utf-8")
    assert run_pipx_cli(["uninstall", "pycowsay"]) == 0
    capsys.readouterr()

    assert run_pipx_cli(["install-all", str(spec_path)]) == 0
    capsys.readouterr()

    assert not (paths.ctx.bin_dir / app_name("pycowsay")).exists()
    assert PipxMetadata(unexposed_pycowsay).exposure_enabled is False


def test_list_reports_unexposed_environment(unexposed_pycowsay: Path, capsys: CaptureFixture[str]) -> None:
    assert run_pipx_cli(["list"]) == 0

    output = capsys.readouterr().out
    assert "apps and manual pages are not exposed" in output
    assert "symlink missing" not in output


def test_unexpose_json(installed_pycowsay: Path, capsys: CaptureFixture[str]) -> None:
    assert run_pipx_cli(["unexpose", "pycowsay", "--json"]) == 0

    assert json.loads(capsys.readouterr().out) == {
        "command": ["unexpose"],
        "data": {
            "environments": [{"environment": "pycowsay", "status": "unexposed"}],
        },
        "pipx_result_version": "1",
        "errors": [],
        "exit_code": 0,
        "status": "success",
    }


def test_expose_reports_collisions_as_partial(unexposed_pycowsay: Path, capsys: CaptureFixture[str]) -> None:
    blocker = paths.ctx.bin_dir / app_name("pycowsay")
    blocker.write_text("not managed by pipx", encoding="utf-8")

    assert run_pipx_cli(["expose", "pycowsay", "--json"]) == 1

    envelope = json.loads(capsys.readouterr().out)
    assert (
        envelope["status"],
        envelope["command"],
        [error["code"] for error in envelope["errors"]],
        (paths.ctx.man_dir / "man6" / "pycowsay.6").exists(),
        blocker.read_text(encoding="utf-8"),
    ) == ("partial", ["expose"], ["environment_expose_conflict"], True, "not managed by pipx")


@pytest.mark.parametrize(
    ("command", "setup_command", "message"),
    [
        pytest.param("expose", None, "pycowsay: already exposed\n", id="expose"),
        pytest.param("unexpose", "unexpose", "pycowsay: already unexposed\n", id="unexpose"),
    ],
)
def test_exposure_command_is_idempotent(
    installed_pycowsay: Path,
    capsys: CaptureFixture[str],
    command: str,
    setup_command: str | None,
    message: str,
) -> None:
    if setup_command is not None:
        assert run_pipx_cli([setup_command, "pycowsay"]) == 0
        capsys.readouterr()

    assert run_pipx_cli([command, "pycowsay"]) == 0

    assert capsys.readouterr().out == message


def test_legacy_environment_defaults_to_exposed(installed_pycowsay: Path) -> None:
    mock_legacy_venv("pycowsay", "0.3")

    assert PipxMetadata(installed_pycowsay).exposure_enabled is True


def test_exposure_command_reports_unreadable_metadata(
    pipx_temp_env: None,
    capsys: CaptureFixture[str],
) -> None:
    (paths.ctx.venvs / "broken").mkdir(parents=True)

    assert run_pipx_cli(["expose", "broken"]) == 1

    assert capsys.readouterr().err == "pipx cannot read metadata for package broken\n"


@pytest.mark.parametrize("command", [pytest.param("expose", id="expose"), pytest.param("unexpose", id="unexpose")])
def test_exposure_command_reports_missing_environment(
    pipx_temp_env: None,
    capsys: CaptureFixture[str],
    command: str,
) -> None:
    assert run_pipx_cli([command, "missing"]) == 1

    assert capsys.readouterr().err == "pipx does not manage package missing\n"
