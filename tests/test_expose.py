from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Final

import pytest

from helpers import app_name, mock_legacy_venv, run_pipx_cli
from package_info import PKG
from pipx import paths
from pipx.pipx_metadata_file import PipxMetadata

if TYPE_CHECKING:
    from pathlib import Path


def test_unexpose_hides_resources(installed_pycowsay: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["unexpose", "pycowsay"]) == 0

    assert (
        (paths.CTX.bin_dir / app_name("pycowsay")).exists(),
        (paths.CTX.man_dir / "man6" / "pycowsay.6").exists(),
        installed_pycowsay.exists(),
        PipxMetadata(installed_pycowsay).exposure_enabled,
        capsys.readouterr().out,
    ) == (False, False, True, False, "pycowsay: unexposed\n")


def test_expose_restores_resources(unexposed_pycowsay: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["expose", "pycowsay"]) == 0

    assert (
        (paths.CTX.bin_dir / app_name("pycowsay")).exists(),
        (paths.CTX.man_dir / "man6" / "pycowsay.6").exists(),
        PipxMetadata(unexposed_pycowsay).exposure_enabled,
        capsys.readouterr().out,
    ) == (True, True, True, "pycowsay: exposed\n")


@pytest.fixture
def unexposed_pycowsay(installed_pycowsay: Path, capsys: pytest.CaptureFixture[str]) -> Path:
    assert run_pipx_cli(["unexpose", "pycowsay"]) == 0
    capsys.readouterr()
    return installed_pycowsay


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_preserves_unexposed_state(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["install", "isort==5.6.4"]) == 0
    assert run_pipx_cli(["unexpose", "isort"]) == 0
    venv_dir: Final[Path] = paths.CTX.venvs / "isort"
    previous_version: Final[str] = PipxMetadata(venv_dir).main_package.package_version
    capsys.readouterr()

    assert run_pipx_cli(["upgrade", "isort"]) == 0
    capsys.readouterr()

    metadata: Final[PipxMetadata] = PipxMetadata(venv_dir)
    assert (
        metadata.main_package.package_version != previous_version,
        (paths.CTX.bin_dir / app_name("isort")).exists(),
        metadata.exposure_enabled,
    ) == (True, False, False)


@pytest.mark.usefixtures("pipx_temp_env")
def test_install_upgrade_preserves_unexposed_state(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["install", PKG["black"]["spec"]]) == 0
    assert run_pipx_cli(["unexpose", "black"]) == 0
    capsys.readouterr()

    assert run_pipx_cli(["install", "--upgrade", "black==22.10.0"]) == 0

    assert (
        "upgraded package black from 22.8.0 to 22.10.0" in capsys.readouterr().out,
        (paths.CTX.bin_dir / app_name("black")).exists(),
        PipxMetadata(paths.CTX.venvs / "black").exposure_enabled,
    ) == (True, False, False)


def test_force_install_preserves_unexposed_state(
    unexposed_pycowsay: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["install", "--force", "pycowsay"]) == 0

    assert (
        "installed package pycowsay" in capsys.readouterr().out,
        (paths.CTX.bin_dir / app_name("pycowsay")).exists(),
        PipxMetadata(unexposed_pycowsay).exposure_enabled,
    ) == (True, False, False)


def test_reinstall_preserves_unexposed_state(
    unexposed_pycowsay: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (marker := unexposed_pycowsay / "marker").touch()

    assert run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"]) == 0
    capsys.readouterr()

    assert (
        marker.exists(),
        (paths.CTX.bin_dir / app_name("pycowsay")).exists(),
        PipxMetadata(unexposed_pycowsay).exposure_enabled,
    ) == (False, False, False)


def test_unexposed_environment_does_not_expose_injected_apps(
    unexposed_pycowsay: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["inject", "--include-apps", "pycowsay", "isort"]) == 0
    capsys.readouterr()

    metadata: Final[PipxMetadata] = PipxMetadata(unexposed_pycowsay)
    assert (
        "isort" in metadata.injected_packages,
        (paths.CTX.bin_dir / app_name("isort")).exists(),
        metadata.exposure_enabled,
    ) == (True, False, False)


def test_install_all_preserves_unexposed_state(
    unexposed_pycowsay: Path,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    assert run_pipx_cli(["list", "--json"]) == 0
    (spec_path := tmp_path / "pipx.json").write_text(capsys.readouterr().out, encoding="utf-8")
    assert run_pipx_cli(["uninstall", "pycowsay"]) == 0
    capsys.readouterr()

    assert run_pipx_cli(["install-all", str(spec_path)]) == 0
    capsys.readouterr()

    assert (
        (paths.CTX.bin_dir / app_name("pycowsay")).exists(),
        PipxMetadata(unexposed_pycowsay).exposure_enabled,
    ) == (False, False)


@pytest.mark.usefixtures("unexposed_pycowsay")
def test_list_reports_unexposed_environment(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["list"]) == 0

    output: Final[str] = capsys.readouterr().out
    assert ("apps and manual pages are not exposed" in output, "symlink missing" in output) == (True, False)


@pytest.mark.usefixtures("installed_pycowsay")
def test_unexpose_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["unexpose", "pycowsay", "--output", "json"]) == 0

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


@pytest.mark.usefixtures("unexposed_pycowsay")
def test_expose_reports_collisions_as_partial(capsys: pytest.CaptureFixture[str]) -> None:
    (blocker := paths.CTX.bin_dir / app_name("pycowsay")).write_text("not managed by pipx", encoding="utf-8")

    assert run_pipx_cli(["expose", "pycowsay", "--output", "json"]) == 1

    envelope: Final = json.loads(capsys.readouterr().out)
    assert (
        envelope["status"],
        envelope["command"],
        [error["code"] for error in envelope["errors"]],
        (paths.CTX.man_dir / "man6" / "pycowsay.6").exists(),
        blocker.read_text(encoding="utf-8"),
    ) == ("partial", ["expose"], ["environment_expose_conflict"], True, "not managed by pipx")


@pytest.mark.parametrize(
    "missing_app",
    [
        pytest.param("app_removed_after_cleared_collision", id="after-cleared-collision"),
        pytest.param("app_removed_by_hand", id="after-manual-delete"),
    ],
)
def test_expose_relinks_missing_app(
    request: pytest.FixtureRequest, capsys: pytest.CaptureFixture[str], missing_app: str
) -> None:
    app: Final[Path] = request.getfixturevalue(missing_app)

    assert (run_pipx_cli(["expose", "pycowsay"]), app.exists(), capsys.readouterr().out) == (
        0,
        True,
        "pycowsay: exposed\n",
    )


@pytest.fixture
def app_removed_after_cleared_collision(unexposed_pycowsay: Path, capsys: pytest.CaptureFixture[str]) -> Path:
    (app := paths.CTX.bin_dir / app_name(unexposed_pycowsay.name)).write_text("not managed by pipx", encoding="utf-8")
    assert run_pipx_cli(["expose", "pycowsay"]) == 1
    capsys.readouterr()
    app.unlink()
    return app


@pytest.fixture
def app_removed_by_hand(installed_pycowsay: Path) -> Path:
    (app := paths.CTX.bin_dir / app_name(installed_pycowsay.name)).unlink()
    return app


@pytest.mark.parametrize(
    ("command", "state", "message"),
    [
        pytest.param("expose", "installed_pycowsay", "pycowsay: already exposed\n", id="expose"),
        pytest.param("unexpose", "unexposed_pycowsay", "pycowsay: already unexposed\n", id="unexpose"),
    ],
)
def test_exposure_command_is_idempotent(
    request: pytest.FixtureRequest,
    capsys: pytest.CaptureFixture[str],
    command: str,
    state: str,
    message: str,
) -> None:
    request.getfixturevalue(state)

    assert run_pipx_cli([command, "pycowsay"]) == 0

    assert capsys.readouterr().out == message


def test_legacy_environment_defaults_to_exposed(installed_pycowsay: Path) -> None:
    mock_legacy_venv("pycowsay", "0.3")

    assert PipxMetadata(installed_pycowsay).exposure_enabled is True


@pytest.mark.usefixtures("pipx_temp_env")
def test_exposure_command_reports_unreadable_metadata(
    capsys: pytest.CaptureFixture[str],
) -> None:
    (paths.CTX.venvs / "broken").mkdir(parents=True)

    assert run_pipx_cli(["expose", "broken"]) == 1

    assert capsys.readouterr().err == "pipx cannot read metadata for package broken\n"


@pytest.mark.parametrize("command", [pytest.param("expose", id="expose"), pytest.param("unexpose", id="unexpose")])
@pytest.mark.usefixtures("pipx_temp_env")
def test_exposure_command_reports_missing_environment(
    capsys: pytest.CaptureFixture[str],
    command: str,
) -> None:
    assert run_pipx_cli([command, "missing"]) == 1

    assert capsys.readouterr().err == "pipx does not manage package missing\n"
