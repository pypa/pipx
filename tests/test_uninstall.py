from __future__ import annotations

import importlib
import json
import sys
from typing import TYPE_CHECKING, Final, cast

import pytest

from helpers import (
    PIPX_METADATA_LEGACY_VERSIONS,
    app_name,
    mock_legacy_venv,
    remove_venv_interpreter,
    run_pipx_cli,
    skip_if_windows,
)
from package_info import PKG
from pipx import paths, venv_inspect

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


def file_or_symlink(filepath: Path) -> bool:
    # Returns True for file or broken symlink or non-broken symlink
    # Returns False for no file and no symlink

    # filepath.exists() returns True for regular file or non-broken symlink
    # filepath.exists() returns False for no regular file or broken symlink
    # filepath.is_symlink() returns True for broken or non-broken symlink
    return filepath.exists() or filepath.is_symlink()


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall() -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["uninstall", "pycowsay"])


def test_uninstall_json(
    uninstall_command: tuple[str, list[str]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    command, arguments = uninstall_command

    assert not run_pipx_cli([command, *arguments, "--output", "json"])

    captured = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": [command],
            "data": {
                "packages": [
                    {
                        "environment": "pycowsay",
                        "location": str(paths.ctx.venvs / "pycowsay"),
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

    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")


@pytest.fixture(
    params=[
        pytest.param(("uninstall", ["pycowsay"]), id="one"),
        pytest.param(("uninstall-all", []), id="all"),
    ]
)
def uninstall_command(
    request: pytest.FixtureRequest,
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # side-effect fixture; usefixtures marks cannot apply to fixtures
    capsys: pytest.CaptureFixture[str],
) -> tuple[str, list[str]]:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()
    return cast("tuple[str, list[str]]", request.param)


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

    captured = capsys.readouterr()
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
    safe_unlink = mocker.patch.object(
        importlib.import_module("pipx.commands.uninstall"),
        "safe_unlink",
        autospec=True,
        side_effect=FileNotFoundError,
    )

    result = run_pipx_cli(["uninstall", "pycowsay"])

    assert (result, (paths.ctx.venvs / "pycowsay").exists(), safe_unlink.call_count > 0) == (0, False, True)


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_global() -> None:
    assert not run_pipx_cli(["install", "--global", "pycowsay"])
    assert not run_pipx_cli(["uninstall", "--global", "pycowsay"])


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_legacy_venv(metadata_version: str | None) -> None:
    executable_path = paths.ctx.bin_dir / app_name("pycowsay")

    assert not run_pipx_cli(["install", "pycowsay"])
    assert executable_path.exists()

    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    assert not run_pipx_cli(["uninstall", "pycowsay"])
    assert not file_or_symlink(executable_path)


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_legacy_venv_inspects_once(mocker: MockerFixture) -> None:
    assert run_pipx_cli(["install", "pycowsay"]) == 0
    executable_path = paths.ctx.bin_dir / app_name("pycowsay")
    assert executable_path.exists()
    mock_legacy_venv("pycowsay")
    run_subprocess = mocker.spy(venv_inspect, "run_subprocess")

    assert run_pipx_cli(["uninstall", "pycowsay"]) == 0

    assert not file_or_symlink(executable_path)
    assert run_subprocess.call_count == 1


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_suffix() -> None:
    name = "pbr"
    suffix = "_a"
    executable_path = paths.ctx.bin_dir / app_name(f"{name}{suffix}")

    assert not run_pipx_cli(["install", PKG[name]["spec"], f"--suffix={suffix}"])
    assert executable_path.exists()

    assert not run_pipx_cli(["uninstall", f"{name}{suffix}"])
    assert not file_or_symlink(executable_path)


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_man_page() -> None:
    man_page_path = paths.ctx.man_dir / "man6" / "pycowsay.6"
    assert not run_pipx_cli(["install", "pycowsay"])
    assert man_page_path.exists()
    assert not run_pipx_cli(["uninstall", "pycowsay"])
    assert not file_or_symlink(man_page_path)


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_removes_selected_dependency_resources(local_extras_project: Path) -> None:
    package: Final[str] = f"{local_extras_project}[tools]"
    assert not run_pipx_cli(["install", package, "--include-resources-from", "pycowsay"])
    exposed_paths: Final[tuple[Path, ...]] = (
        paths.ctx.bin_dir / app_name("repeatme"),
        paths.ctx.bin_dir / app_name("pycowsay"),
        paths.ctx.man_dir / "man6" / "pycowsay.6",
    )
    assert all(file_or_symlink(path) for path in exposed_paths)

    assert not run_pipx_cli(["uninstall", "repeatme"])

    assert not any(file_or_symlink(path) for path in exposed_paths)


def test_uninstall_preserves_colliding_dependency_resource(
    copied_dependency_resource: tuple[Path, bytes],
    local_extras_project: Path,
) -> None:
    exposed_app: Final[Path] = copied_dependency_resource[0]
    first_contents: Final[bytes] = copied_dependency_resource[1]
    assert not run_pipx_cli(["install", f"{local_extras_project}[cow]", "--include-deps"])

    assert not run_pipx_cli(["uninstall", "repeatme"])

    assert exposed_app.read_bytes() == first_contents


@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_injected() -> None:
    pycowsay_app_paths = [paths.ctx.bin_dir / app for app in PKG["pycowsay"]["apps"]]
    pycowsay_man_page_paths = [paths.ctx.man_dir / man_page for man_page in PKG["pycowsay"]["man_pages"]]
    pylint_app_paths = [paths.ctx.bin_dir / app for app in PKG["pylint"]["apps"]]
    app_paths = pycowsay_app_paths + pylint_app_paths
    man_page_paths = pycowsay_man_page_paths

    assert not run_pipx_cli(["install", PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["inject", "--include-apps", "pycowsay", PKG["pylint"]["spec"]])

    for app_path in app_paths:
        assert app_path.exists()

    for man_page_path in man_page_paths:
        assert man_page_path.exists()

    assert not run_pipx_cli(["uninstall", "pycowsay"])

    for app_path in app_paths:
        assert not file_or_symlink(app_path)

    for man_page_path in man_page_paths:
        assert not file_or_symlink(man_page_path)


@pytest.mark.parametrize("metadata_version", ["0.1"])
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_suffix_legacy_venv(metadata_version: str) -> None:
    name = "pbr"
    # legacy uninstall on Windows only works with "canonical name characters"
    #   in suffix
    suffix = "-a"
    executable_path = paths.ctx.bin_dir / app_name(f"{name}{suffix}")

    assert not run_pipx_cli(["install", PKG[name]["spec"], f"--suffix={suffix}"])
    mock_legacy_venv(f"{name}{suffix}", metadata_version=metadata_version)
    assert executable_path.exists()

    assert not run_pipx_cli(["uninstall", f"{name}{suffix}"])
    assert not file_or_symlink(executable_path)


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_with_missing_interpreter(metadata_version: str | None) -> None:
    executable_path = paths.ctx.bin_dir / app_name("pycowsay")

    assert not run_pipx_cli(["install", "pycowsay"])
    assert executable_path.exists()

    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    remove_venv_interpreter("pycowsay")

    assert not run_pipx_cli(["uninstall", "pycowsay"])
    # On Windows we cannot remove app binaries if no metadata and no python
    if not (sys.platform.startswith("win") and metadata_version is None):
        assert not file_or_symlink(executable_path)


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_proper_dep_behavior(metadata_version: str | None) -> None:
    # isort is a dependency of pylint.  Make sure that uninstalling pylint
    #   does not also uninstall isort app in LOCAL_BIN_DIR
    isort_app_paths = [paths.ctx.bin_dir / app for app in PKG["isort"]["apps"]]
    pylint_app_paths = [paths.ctx.bin_dir / app for app in PKG["pylint"]["apps"]]

    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    assert not run_pipx_cli(["install", PKG["isort"]["spec"]])
    mock_legacy_venv("pylint", metadata_version=metadata_version)
    mock_legacy_venv("isort", metadata_version=metadata_version)
    for pylint_app_path in pylint_app_paths:
        assert pylint_app_path.exists()
    for isort_app_path in isort_app_paths:
        assert isort_app_path.exists()

    assert not run_pipx_cli(["uninstall", "pylint"])

    for pylint_app_path in pylint_app_paths:
        assert not file_or_symlink(pylint_app_path)
    # THIS is what we're making sure is true:
    for isort_app_path in isort_app_paths:
        assert isort_app_path.exists()


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_proper_dep_behavior_missing_interpreter(metadata_version: str | None) -> None:
    # isort is a dependency of pylint.  Make sure that uninstalling pylint
    #   does not also uninstall isort app in LOCAL_BIN_DIR
    isort_app_paths = [paths.ctx.bin_dir / app for app in PKG["isort"]["apps"]]
    pylint_app_paths = [paths.ctx.bin_dir / app for app in PKG["pylint"]["apps"]]

    assert not run_pipx_cli(["install", PKG["pylint"]["spec"]])
    assert not run_pipx_cli(["install", PKG["isort"]["spec"]])
    mock_legacy_venv("pylint", metadata_version=metadata_version)
    mock_legacy_venv("isort", metadata_version=metadata_version)
    remove_venv_interpreter("pylint")
    remove_venv_interpreter("isort")
    for pylint_app_path in pylint_app_paths:
        assert pylint_app_path.exists()
    for isort_app_path in isort_app_paths:
        assert isort_app_path.exists()

    assert not run_pipx_cli(["uninstall", "pylint"])

    # Do not check the following on Windows without metadata, we do not
    #   remove bin dir links by design for missing interpreter in that case
    if not (sys.platform.startswith("win") and metadata_version is None):
        for pylint_app_path in pylint_app_paths:
            assert not file_or_symlink(pylint_app_path)
    # THIS is what we're making sure is true:
    for isort_app_path in isort_app_paths:
        assert isort_app_path.exists()
