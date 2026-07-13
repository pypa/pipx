import shutil
import subprocess
from pathlib import Path
from typing import Final

import pytest

from helpers import app_name, run_pipx_cli, skip_if_windows
from package_info import PKG
from pipx import paths
from pipx.constants import WINDOWS


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


def test_uninject_with_suffix_removes_apps(pipx_temp_env: None, root: Path, tmp_path: Path) -> None:
    suffix = "@1"
    ignore_generated = shutil.ignore_patterns("build", "*.egg-info")
    project = shutil.copytree(root / "testdata/empty_project", tmp_path / "empty_project", ignore=ignore_generated)
    assert not run_pipx_cli(["install", str(project), f"--suffix={suffix}"])
    injected_project = shutil.copytree(
        root / "testdata/test_package_specifier/local_extras",
        tmp_path / "local_extras",
        ignore=ignore_generated,
    )
    assert not run_pipx_cli(
        [
            "inject",
            f"empty-project{suffix}",
            f"{injected_project}[cow]",
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
