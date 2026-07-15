from __future__ import annotations

import json
import shutil
import subprocess
from typing import TYPE_CHECKING, Final

import pytest

from helpers import app_name, mock_legacy_venv, run_pipx_cli, skip_if_windows
from package_info import PKG
from pipx import paths
from pipx.constants import WINDOWS
from pipx.util import pipx_wrap

if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.capture import CaptureResult


def test_uninject_json(installed_pycowsay: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    capsys.readouterr()

    assert not run_pipx_cli(["uninject", "--output", "json", "pycowsay", "black"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["uninject"],
            "data": {
                "packages": [
                    {
                        "environment": "pycowsay",
                        "location": str(paths.ctx.venvs / "pycowsay"),
                        "package": "black",
                        "status": "uninjected",
                        "version": "22.8.0",
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


def test_uninject_json_reports_unknown_package(
    installed_pycowsay: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["uninject", "--output", "json", "pycowsay", "missing"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["uninject"],
            "data": {"packages": [], "skipped": []},
            "errors": [
                {
                    "code": "package_uninject_failed",
                    "environment": "pycowsay",
                    "message": "missing is not in the pycowsay venv. Skipping.",
                    "package": "missing",
                }
            ],
            "exit_code": 1,
            "pipx_result_version": "1",
            "status": "error",
        },
        "",
    )


def test_uninject_json_reports_missing_environment(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["uninject", "--output", "json", "missing", "black"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["uninject"],
            "data": {"packages": [], "skipped": []},
            "errors": [
                {
                    "code": "package_uninject_failed",
                    "environment": "missing",
                    "message": "Virtual environment missing does not exist.",
                    "package": None,
                }
            ],
            "exit_code": 1,
            "pipx_result_version": "1",
            "status": "error",
        },
        "",
    )


def test_uninject_json_reports_missing_metadata(
    installed_pycowsay: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_legacy_venv("pycowsay")

    assert run_pipx_cli(["uninject", "--output", "json", "pycowsay", "black"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["uninject"],
            "data": {"packages": [], "skipped": []},
            "errors": [
                {
                    "code": "package_uninject_failed",
                    "environment": "pycowsay",
                    "message": pipx_wrap(
                        """
                        Can't uninject from Virtual Environment 'pycowsay'.
                        'pycowsay' has missing internal pipx metadata.
                        It was likely installed using a pipx version before 0.15.0.0.
                        Please uninstall and install 'pycowsay' manually to fix.
                        """
                    ),
                    "package": None,
                }
            ],
            "exit_code": 1,
            "pipx_result_version": "1",
            "status": "error",
        },
        "",
    )


def test_uninject_json_reports_main_package(
    installed_pycowsay: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_pipx_cli(["uninject", "--output", "json", "pycowsay", "pycowsay"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["uninject"],
            "data": {"packages": [], "skipped": []},
            "errors": [
                {
                    "code": "package_uninject_failed",
                    "environment": "pycowsay",
                    "message": pipx_wrap(
                        """
                        pycowsay is the main package of pycowsay
                        venv. Use `pipx uninstall pycowsay` to uninstall instead of uninject.
                        """,
                        subsequent_indent=" " * 4,
                    ),
                    "package": "pycowsay",
                }
            ],
            "exit_code": 1,
            "pipx_result_version": "1",
            "status": "error",
        },
        "",
    )


def test_uninject_quiet(installed_pycowsay: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["inject", "pycowsay", "black"])
    capsys.readouterr()

    assert not run_pipx_cli(["uninject", "-qq", "pycowsay", "black"])

    assert "Uninjected package" not in capsys.readouterr().out


@pytest.fixture
def installed_pycowsay(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()


def file_or_symlink(filepath: Path) -> bool:
    return filepath.exists() or filepath.is_symlink()


def test_uninject_simple(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    assert not run_pipx_cli(["uninject", "pycowsay", "black"])
    captured = capsys.readouterr()
    assert "Uninjected package black" in captured.out
    assert not run_pipx_cli(["list", "--include-injected"])
    captured = capsys.readouterr()
    assert "black" not in captured.out


@skip_if_windows
def test_uninject_simple_global(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "--global", "pycowsay"])
    assert not run_pipx_cli(["inject", "--global", "pycowsay", PKG["black"]["spec"]])
    assert not run_pipx_cli(["uninject", "--global", "pycowsay", "black"])
    captured = capsys.readouterr()
    assert "Uninjected package black" in captured.out
    assert not run_pipx_cli(["list", "--global", "--include-injected"])
    captured = capsys.readouterr()
    assert "black" not in captured.out


def test_uninject_with_include_apps(pipx_temp_env, capsys, caplog):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"], "--include-deps", "--include-apps"])
    assert not run_pipx_cli(["uninject", "pycowsay", "black", "--verbose"])
    assert "removed file" in caplog.text


@pytest.mark.skipif(not WINDOWS, reason="Windows-specific test")
def test_uninject_running_app(pipx_temp_env: None) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"], "--include-apps"])
    app = paths.ctx.bin_dir / app_name("black")

    process = subprocess.Popen(
        [app, "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        assert process.poll() is None
        assert not run_pipx_cli(["uninject", "pycowsay", "black"])
        assert not app.exists()
    finally:
        process.terminate()
        process.wait(timeout=10)


def test_uninject_with_suffix_removes_apps(
    pipx_temp_env: None,
    root: Path,
    tmp_path: Path,
    local_extras_project: Path,
) -> None:
    suffix = "@1"
    project = shutil.copytree(
        root / "testdata/empty_project",
        tmp_path / "empty_project",
        ignore=shutil.ignore_patterns("build", "*.egg-info"),
    )
    assert not run_pipx_cli(["install", str(project), f"--suffix={suffix}"])
    assert not run_pipx_cli(
        [
            "inject",
            f"empty-project{suffix}",
            f"{local_extras_project}[cow]",
            "--include-deps",
            "--with-suffix",
        ]
    )
    app_paths = {paths.ctx.bin_dir / app_name(f"{app}{suffix}") for app in ("pycowsay", "repeatme")}
    assert all(file_or_symlink(path) for path in app_paths)
    assert not run_pipx_cli(["uninject", f"empty-project{suffix}", f"repeatme{suffix}"])
    assert not any(file_or_symlink(path) for path in app_paths)


def test_uninject_man_page(pipx_temp_env):
    # Regression: uninject must remove the injected package's man page symlinks,
    # not only its app symlinks. pycowsay ships man6/pycowsay.6.
    man_page_paths = [paths.ctx.man_dir / man_page for man_page in PKG["pycowsay"]["man_pages"]]
    assert not run_pipx_cli(["install", PKG["black"]["spec"]])
    assert not run_pipx_cli(["inject", "black", "pycowsay", "--include-apps"])
    for man_page_path in man_page_paths:
        assert man_page_path.exists()
    assert not run_pipx_cli(["uninject", "black", "pycowsay"])
    for man_page_path in man_page_paths:
        assert not file_or_symlink(man_page_path)


def test_uninject_removes_dependency_app_symlinks(pipx_temp_env, capsys, caplog):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["pylint"]["spec"], "--include-deps", "--include-apps"])
    captured = capsys.readouterr()
    assert "isort" in captured.out
    assert not run_pipx_cli(["uninject", "pycowsay", "pylint", "--verbose"])
    assert "removed file" in caplog.text
    assert "isort" in caplog.text


def test_uninject_removes_selected_dependency_resources(
    pipx_temp_env: None,
    local_extras_project: Path,
    empty_project: Path,
) -> None:
    package: Final[str] = f"{local_extras_project}[tools]"
    assert not run_pipx_cli(["install", str(empty_project)])
    assert not run_pipx_cli(["inject", "empty-project", package, "--include-apps-from", "pycowsay"])
    exposed_paths: Final[tuple[Path, ...]] = (
        paths.ctx.bin_dir / app_name("repeatme"),
        paths.ctx.bin_dir / app_name("pycowsay"),
        paths.ctx.man_dir / "man6" / "pycowsay.6",
    )
    assert all(file_or_symlink(path) for path in exposed_paths)

    assert not run_pipx_cli(["uninject", "empty-project", "repeatme"])

    assert not any(file_or_symlink(path) for path in exposed_paths)


def test_uninject_leave_deps(pipx_temp_env, capsys, caplog):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    assert not run_pipx_cli(["uninject", "pycowsay", "black", "--leave-deps", "--verbose"])
    captured = capsys.readouterr()
    assert "Uninjected package black from venv pycowsay" in captured.out
    assert "Dependencies of uninstalled package:" not in caplog.text


def test_uninject_preserves_shared_deps(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    assert not run_pipx_cli(["inject", "pycowsay", PKG["pylint"]["spec"]])
    assert not run_pipx_cli(["uninject", "pycowsay", "black"])
    capsys.readouterr()
    assert not run_pipx_cli(["list", "--include-injected"])
    captured = capsys.readouterr()
    assert "pylint" in captured.out
    assert "black" not in captured.out
