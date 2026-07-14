import subprocess
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Final

import pytest
from pytest_mock import MockerFixture

from helpers import PIPX_METADATA_LEGACY_VERSIONS, app_name, mock_legacy_venv, run_pipx_cli, skip_if_windows
from pipx import paths, util, venv_inspect
from pipx.pipx_metadata_file import PackageInfo, PipxMetadata


def test_reinstall(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])


def test_reinstall_inline_script(pipx_temp_env: None, inline_script: Path) -> None:
    assert not run_pipx_cli(["install", str(inline_script)])
    inline_script.write_text(
        inline_script.read_text(encoding="utf-8").replace("installed", "reinstalled"),
        encoding="utf-8",
    )

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "hello"])

    process: Final[subprocess.CompletedProcess[str]] = subprocess.run(
        [paths.ctx.bin_dir / app_name("hello")],
        check=True,
        capture_output=True,
        text=True,
    )
    assert process.stdout == "reinstalled\n"


def test_reinstall_preserves_cooldowns(
    pipx_temp_env: None,
    root: Path,
    empty_project: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    find_links: Final[Path] = (
        root / ".pipx_tests" / "package_cache" / f"{sys.version_info.major}.{sys.version_info.minor}"
    )
    pip_args: Final[str] = f"--pip-args=--no-index --find-links={find_links}"
    assert not run_pipx_cli(["install", "--cooldown", "7", pip_args, "pycowsay"])
    assert not run_pipx_cli(["inject", "--cooldown", "5", pip_args, "pycowsay", str(empty_project)])
    caplog.clear()

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "pycowsay")
    assert (
        "--uploaded-prior-to P7D" in caplog.text,
        "--uploaded-prior-to P5D" in caplog.text,
        metadata.main_package.cooldown_days,
        metadata.injected_packages["empty-project"].cooldown_days,
    ) == (True, True, 7, 5)


def test_reinstall_pylock_restores_source_after_build_failure(
    pipx_temp_env: None,
    make_pylock: Callable[[str, str], Path],
    make_project_with_dependency: Callable[[str], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = make_project_with_dependency("pycowsay==0.0.0.2")
    lock_file = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--lock", str(lock_file), str(project)])
    capsys.readouterr()
    pyproject = project / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace("setuptools.build_meta", "missing"),
        encoding="utf-8",
    )

    assert run_pipx_cli(["reinstall", "empty-project"])

    metadata = PipxMetadata(paths.ctx.venvs / "empty-project").main_package
    assert (
        "Reinstall failed; restored empty-project" in capsys.readouterr().err,
        metadata.package_version,
        metadata.lock_file,
        (paths.ctx.bin_dir / app_name("empty-project")).exists(),
    ) == (True, "0.1.0", lock_file.resolve(), True)


@skip_if_windows
def test_reinstall_global(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "--global", "pycowsay"])
    assert not run_pipx_cli(["reinstall", "--global", "--python", sys.executable, "pycowsay"])


def test_reinstall_nonexistent(pipx_temp_env, capsys):
    assert run_pipx_cli(["reinstall", "--python", sys.executable, "nonexistent"])
    assert "Nothing to reinstall for nonexistent" in capsys.readouterr().out


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
def test_reinstall_legacy_venv(pipx_temp_env, capsys, metadata_version):
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])


def test_reinstall_legacy_venv_inspects_once_for_resources(pipx_temp_env: None, mocker: MockerFixture) -> None:
    assert run_pipx_cli(["install", "pycowsay"]) == 0
    executable_path = paths.ctx.bin_dir / app_name("pycowsay")
    mock_legacy_venv("pycowsay")
    run_subprocess = mocker.spy(venv_inspect, "run_subprocess")

    assert run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"]) == 0

    assert executable_path.exists()
    assert run_subprocess.call_count == 2


def test_reinstall_suffix(pipx_temp_env, capsys):
    suffix = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, f"pycowsay{suffix}"])


@pytest.mark.parametrize("metadata_version", ["0.1"])
def test_reinstall_suffix_legacy_venv(pipx_temp_env, capsys, metadata_version):
    suffix = "_x"
    assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])
    mock_legacy_venv(f"pycowsay{suffix}", metadata_version=metadata_version)

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, f"pycowsay{suffix}"])


def test_reinstall_specifier(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pylint==3.0.4"])

    # clear capsys before reinstall
    captured = capsys.readouterr()

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pylint"])
    captured = capsys.readouterr()
    assert "installed package pylint 3.0.4" in captured.out


def test_reinstall_preserves_included_dependency(pipx_temp_env: None, local_extras_project: Path) -> None:
    package: Final[str] = f"{local_extras_project}[tools]"
    assert not run_pipx_cli(["install", package, "--include-apps-from", "pycowsay"])

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "repeatme"])

    metadata: Final[PackageInfo] = PipxMetadata(paths.ctx.venvs / "repeatme").main_package
    assert (
        metadata.include_apps_from,
        (paths.ctx.bin_dir / app_name("pycowsay")).exists(),
        (paths.ctx.bin_dir / app_name("black")).exists(),
    ) == (["pycowsay"], True, False)


@skip_if_windows
def test_reinstall_removes_stale_apps_after_success(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    venv_dir = paths.ctx.venvs / "pycowsay"
    stale_app_name = app_name("removed-cowsay")
    stale_app_path = util.get_venv_paths(venv_dir)[0] / stale_app_name
    stale_app_path.write_text("#!/bin/sh\n")
    stale_app_path.chmod(0o755)

    stale_exposed_path = paths.ctx.bin_dir / stale_app_name
    stale_exposed_path.symlink_to(stale_app_path)

    metadata = PipxMetadata(venv_dir)
    metadata.main_package = replace(
        metadata.main_package,
        apps=[*metadata.main_package.apps, stale_app_name],
        app_paths=[*metadata.main_package.app_paths, stale_app_path],
    )
    metadata.write()

    assert not run_pipx_cli(["reinstall", "--python", sys.executable, "pycowsay"])

    assert not stale_exposed_path.exists()
    assert not stale_exposed_path.is_symlink()


def test_reinstall_with_path(pipx_temp_env, capsys, tmp_path):
    path = tmp_path / "some" / "path"

    assert run_pipx_cli(["reinstall", str(path)])
    captured = capsys.readouterr()

    assert "Expected the name of an installed package" in captured.err.replace("\n", " ")

    assert run_pipx_cli(["reinstall", str(path.resolve())])
    captured = capsys.readouterr()

    assert "Expected the name of an installed package" in captured.err.replace("\n", " ")


def test_reinstall_pinned_package(pipx_temp_env, capsys):
    assert not run_pipx_cli(["install", "black"])
    assert not run_pipx_cli(["pin", "black"])
    assert run_pipx_cli(["reinstall", "black"])
    captured = capsys.readouterr()
    assert "pinned" in captured.err

    assert not run_pipx_cli(["unpin", "black"])
    assert not run_pipx_cli(["reinstall", "black"])
    captured = capsys.readouterr()
    assert "installed package black" in captured.out
