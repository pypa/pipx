from __future__ import annotations

import importlib
import json
import sys
from typing import TYPE_CHECKING, Final

import pytest

from helpers import (
    PIPX_METADATA_LEGACY_VERSIONS,
    SKIP_IF_WINDOWS,
    app_name,
    file_or_symlink,
    mock_legacy_venv,
    remove_venv_interpreter,
    run_pipx_cli,
)
from package_info import PKG
from pipx import paths, venv_inspect
from pipx.util import get_venv_paths

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall() -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["uninstall", "pycowsay"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_empty_name_keeps_every_environment() -> None:
    assert not run_pipx_cli(["install", "pycowsay"])

    assert (run_pipx_cli(["uninstall", ""]), (paths.CTX.venvs / "pycowsay").is_dir()) == (1, True)


def test_uninstall_json(
    uninstall_command: tuple[str, list[str]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    command, arguments = uninstall_command

    assert not run_pipx_cli([command, *arguments, "--output", "json"])

    captured: Final = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": [command],
            "data": {
                "packages": [
                    {
                        "environment": "pycowsay",
                        "location": str(paths.CTX.venvs / "pycowsay"),
                        "package": "pycowsay",
                        "version": "0.0.0.2",
                    }
                ],
            },
            "pipx_result_version": "1",
            "errors": [],
            "exit_code": 0,
            "status": "success",
        },
        "",
    )


def test_uninstall_quiet(
    uninstall_command: tuple[str, list[str]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    command, arguments = uninstall_command

    assert not run_pipx_cli([command, *arguments, "--quiet"])

    captured: Final = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")


@pytest.fixture(
    params=[
        pytest.param(("uninstall", ["pycowsay"]), id="one"),
        pytest.param(("uninstall-all", []), id="all"),
    ]
)
def uninstall_command(
    request: pytest.FixtureRequest,
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # usefixtures marks do not apply to fixtures
    capsys: pytest.CaptureFixture[str],
) -> tuple[str, list[str]]:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()
    return request.param


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_json_reports_missing(
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        importlib.import_module("pipx.commands.uninstall"),
        "which",
        autospec=True,
        return_value="/usr/bin/missing",
    )
    assert run_pipx_cli(["uninstall", "missing", "--output", "json"])

    captured: Final = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["uninstall"],
            "data": {"packages": []},
            "errors": [
                {
                    "code": "environment_uninstall_failed",
                    "environment": "missing",
                    "message": "Nothing to uninstall for missing.",
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
def test_uninstall_ignores_disappearing_resources(
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()
    safe_unlink: Final = mocker.patch.object(
        importlib.import_module("pipx.commands.uninstall"),
        "safe_unlink",
        autospec=True,
        side_effect=FileNotFoundError,
    )

    assert (
        run_pipx_cli(["uninstall", "pycowsay"]),
        (paths.CTX.venvs / "pycowsay").exists(),
        safe_unlink.call_count > 0,
    ) == (0, False, True)


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_global() -> None:
    assert not run_pipx_cli(["install", "--global", "pycowsay"])
    assert not run_pipx_cli(["uninstall", "--global", "pycowsay"])


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_legacy_venv(metadata_version: str | None) -> None:
    executable_path: Final[Path] = paths.CTX.bin_dir / app_name("pycowsay")

    assert not run_pipx_cli(["install", "pycowsay"])
    assert executable_path.exists()

    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    assert not run_pipx_cli(["uninstall", "pycowsay"])
    assert not file_or_symlink(executable_path)


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_legacy_venv_inspects_once(mocker: MockerFixture) -> None:
    assert run_pipx_cli(["install", "pycowsay"]) == 0
    executable_path: Final[Path] = paths.CTX.bin_dir / app_name("pycowsay")
    assert executable_path.exists()
    mock_legacy_venv("pycowsay")
    run_subprocess: Final = mocker.spy(venv_inspect, "run_subprocess")

    assert run_pipx_cli(["uninstall", "pycowsay"]) == 0

    assert (file_or_symlink(executable_path), run_subprocess.call_count) == (False, 1)


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_suffix() -> None:
    name: Final[str] = "pbr"
    suffix: Final[str] = "_a"
    executable_path: Final[Path] = paths.CTX.bin_dir / app_name(f"{name}{suffix}")

    assert not run_pipx_cli(["install", PKG[name]["spec"], f"--suffix={suffix}"])
    assert executable_path.exists()

    assert not run_pipx_cli(["uninstall", f"{name}{suffix}"])
    assert not file_or_symlink(executable_path)


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_man_page() -> None:
    man_page_path: Final[Path] = paths.CTX.man_dir / "man6" / "pycowsay.6"
    assert not run_pipx_cli(["install", "pycowsay"])
    assert man_page_path.exists()
    assert not run_pipx_cli(["uninstall", "pycowsay"])
    assert not file_or_symlink(man_page_path)


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_removes_selected_dependency_resources(local_extras_wheel: Path) -> None:
    package: Final[str] = f"{local_extras_wheel}[tools]"
    assert not run_pipx_cli(["install", package, "--include-resources-from", "pycowsay"])
    exposed_paths: Final[tuple[Path, ...]] = (
        paths.CTX.bin_dir / app_name("repeatme"),
        paths.CTX.bin_dir / app_name("pycowsay"),
        paths.CTX.man_dir / "man6" / "pycowsay.6",
    )
    assert all(file_or_symlink(path) for path in exposed_paths)

    assert not run_pipx_cli(["uninstall", "repeatme"])

    assert not any(file_or_symlink(path) for path in exposed_paths)


def test_uninstall_preserves_colliding_dependency_resource(
    copied_dependency_resource: tuple[Path, bytes],
    local_extras_wheel: Path,
) -> None:
    exposed_app, first_contents = copied_dependency_resource
    assert not run_pipx_cli(["install", f"{local_extras_wheel}[cow]", "--include-deps"])

    assert not run_pipx_cli(["uninstall", "repeatme"])

    assert exposed_app.read_bytes() == first_contents


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_injected() -> None:
    exposed_paths: Final[list[Path]] = [
        *(paths.CTX.bin_dir / app for app in [*PKG["pycowsay"]["apps"], *PKG["isort"]["apps"]]),
        *(paths.CTX.man_dir / man_page for man_page in PKG["pycowsay"]["man_pages"]),
    ]

    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["inject", "--include-apps", "pycowsay", PKG["isort"]["spec"]])
    assert all(path.exists() for path in exposed_paths)

    assert not run_pipx_cli(["uninstall", "pycowsay"])

    assert not any(file_or_symlink(path) for path in exposed_paths)


@pytest.mark.parametrize("metadata_version", ["0.1"])
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_suffix_legacy_venv(metadata_version: str) -> None:
    name: Final[str] = "pbr"
    # on Windows a legacy uninstall works only with canonical name characters in the suffix
    suffix: Final[str] = "-a"
    executable_path: Final[Path] = paths.CTX.bin_dir / app_name(f"{name}{suffix}")

    assert not run_pipx_cli(["install", PKG[name]["spec"], f"--suffix={suffix}"])
    mock_legacy_venv(f"{name}{suffix}", metadata_version=metadata_version)
    assert executable_path.exists()

    assert not run_pipx_cli(["uninstall", f"{name}{suffix}"])
    assert not file_or_symlink(executable_path)


@SKIP_IF_WINDOWS
@pytest.mark.parametrize(
    "command",
    [pytest.param(["uninstall", "pycowsay"], id="uninstall"), pytest.param(["uninstall-all"], id="uninstall-all")],
)
@pytest.mark.parametrize(
    ("interpreter", "reason"),
    [
        pytest.param(b"#!/bin/sh\necho not json\n", "cannot parse", id="unparsable-output"),
        pytest.param(b"#!/bin/sh\nexit 1\n", "exited with code 1", id="failing"),
        pytest.param(b"", "Unable to run", id="not-executable"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_removes_venv_it_cannot_inspect(
    capsys: pytest.CaptureFixture[str], command: list[str], interpreter: bytes, reason: str
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay")
    remove_venv_interpreter("pycowsay")
    (python := get_venv_paths(paths.CTX.venvs / "pycowsay")[1]).write_bytes(interpreter)
    python.chmod(0o755)
    capsys.readouterr()

    assert (
        run_pipx_cli(command),
        reason in capsys.readouterr().err,
        (paths.CTX.venvs / "pycowsay").exists(),
        file_or_symlink(paths.CTX.bin_dir / app_name("pycowsay")),
    ) == (0, True, False, False)


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_with_missing_interpreter(metadata_version: str | None) -> None:
    executable_path: Final[Path] = paths.CTX.bin_dir / app_name("pycowsay")

    assert not run_pipx_cli(["install", "pycowsay"])
    assert executable_path.exists()

    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    remove_venv_interpreter("pycowsay")

    assert not run_pipx_cli(["uninstall", "pycowsay"])
    # on Windows, without metadata and python, pipx cannot tell which app binaries the environment owns
    if not (sys.platform.startswith("win") and metadata_version is None):
        assert not file_or_symlink(executable_path)


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_proper_dep_behavior(metadata_version: str | None) -> None:
    # isort is a dependency of pylint, so its apps are in both environments
    isort_app_paths: Final[list[Path]] = [paths.CTX.bin_dir / app for app in PKG["isort"]["apps"]]
    pylint_app_paths: Final[list[Path]] = [paths.CTX.bin_dir / app for app in PKG["pylint"]["apps"]]

    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    assert not run_pipx_cli(["install", PKG["isort"]["spec"]])
    mock_legacy_venv("pylint", metadata_version=metadata_version)
    mock_legacy_venv("isort", metadata_version=metadata_version)
    assert all(path.exists() for path in [*pylint_app_paths, *isort_app_paths])

    assert not run_pipx_cli(["uninstall", "pylint"])

    assert (
        any(file_or_symlink(path) for path in pylint_app_paths),
        all(path.exists() for path in isort_app_paths),
    ) == (False, True)


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_proper_dep_behavior_missing_interpreter(metadata_version: str | None) -> None:
    # isort is a dependency of pylint, so its apps are in both environments
    isort_app_paths: Final[list[Path]] = [paths.CTX.bin_dir / app for app in PKG["isort"]["apps"]]
    pylint_app_paths: Final[list[Path]] = [paths.CTX.bin_dir / app for app in PKG["pylint"]["apps"]]

    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    assert not run_pipx_cli(["install", PKG["isort"]["spec"]])
    mock_legacy_venv("pylint", metadata_version=metadata_version)
    mock_legacy_venv("isort", metadata_version=metadata_version)
    remove_venv_interpreter("pylint")
    remove_venv_interpreter("isort")
    assert all(path.exists() for path in [*pylint_app_paths, *isort_app_paths])

    assert not run_pipx_cli(["uninstall", "pylint"])

    # on Windows, without metadata and python, pipx cannot tell which app binaries the environment owns
    if not (sys.platform.startswith("win") and metadata_version is None):
        assert not any(file_or_symlink(path) for path in pylint_app_paths)
    assert all(path.exists() for path in isort_app_paths)


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_killed_midway_leaves_nothing_for_reinstall_to_guess(mocker: MockerFixture) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])

    def lose_the_record_then_die(path: Path, **_kwargs: bool) -> None:
        (path / "pipx_metadata.json").unlink()
        raise KeyboardInterrupt

    mocker.patch("pipx.trash.shutil.rmtree", autospec=True, side_effect=lose_the_record_then_die)
    assert run_pipx_cli(["uninstall", "pycowsay"])
    mocker.stopall()

    assert run_pipx_cli(["reinstall", "pycowsay"])
