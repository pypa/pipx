from __future__ import annotations

import json
import subprocess
import sys
from threading import Barrier
from typing import TYPE_CHECKING, Final

import pytest

from helpers import PIPX_METADATA_LEGACY_VERSIONS, mock_legacy_venv, run_pipx_cli
from package_info import PKG
from pipx import paths
from pipx.pipx_metadata_file import PipxMetadata

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path
    from unittest.mock import MagicMock

    from _pytest.capture import CaptureResult
    from pytest_mock import MockerFixture


def test_upgrade_all(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["upgrade", "pycowsay"])
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["upgrade-all"])


def test_upgrade_all_none(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["upgrade-all"])
    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert "No packages upgraded after running 'pipx upgrade-all'" in captured.out


def test_upgrade_all_checks_current_packages_concurrently(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    for suffix in ("_one", "_two", "_three"):
        assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])
    capsys.readouterr()
    barrier: Final[Barrier] = Barrier(3)

    def check_package(
        cmd: Sequence[str | Path],
        capture_stdout: bool = True,
        capture_stderr: bool = True,
        log_cmd_str: str | None = None,
        log_stdout: bool = True,
        log_stderr: bool = True,
        run_dir: str | None = None,
        env_overrides: dict[str, str | None] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del capture_stdout, capture_stderr, log_cmd_str, log_stdout, log_stderr, run_dir, env_overrides
        assert "list" in cmd and "--outdated" in cmd
        barrier.wait(timeout=5)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="[]", stderr="")

    check: Final[MagicMock] = mocker.patch("pipx.backends.pip.run_subprocess", autospec=True, side_effect=check_package)

    assert (run_pipx_cli(["upgrade-all"]), check.call_count) == (0, 3)


def test_upgrade_all_does_not_copy_current_environment(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    assert not run_pipx_cli(["install", "--app", "pycowsay", "pycowsay"])
    capsys.readouterr()
    mocker.patch(
        "pipx.backends.pip.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=["pip", "list"], returncode=0, stdout="[]", stderr=""),
    )
    backup: Final[MagicMock] = mocker.patch("pipx.commands.transaction.copytree", autospec=True)

    assert (run_pipx_cli(["upgrade-all"]), backup.call_count) == (0, 0)


def test_upgrade_all_updates_current_cooldowns(
    pipx_temp_env: None,
    root: Path,
    mocker: MockerFixture,
) -> None:
    find_links: Final[Path] = (
        root / ".pipx_tests" / "package_cache" / f"{sys.version_info.major}.{sys.version_info.minor}"
    )
    pip_args: Final[str] = f"--pip-args=--no-index --find-links={find_links}"
    assert not run_pipx_cli(["install", "--cooldown", "7", pip_args, PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["inject", "--cooldown", "5", pip_args, "pycowsay", PKG["black"]["spec"]])
    mocker.patch(
        "pipx.backends.pip.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=["pip", "list"], returncode=0, stdout="[]", stderr=""),
    )

    assert not run_pipx_cli(["upgrade-all", "--include-injected", "--cooldown", "0"])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "pycowsay")
    assert (metadata.main_package.cooldown_days, metadata.injected_packages["black"].cooldown_days) == (0, 0)


@pytest.mark.parametrize("injected", [pytest.param(False, id="main"), pytest.param(True, id="injected")])
def test_upgrade_all_upgrades_outdated_package(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
    injected: bool,
) -> None:
    if injected:
        assert not run_pipx_cli(["install", "pycowsay"])
        assert not run_pipx_cli(["inject", "pycowsay", PKG["black"]["spec"]])
    else:
        assert not run_pipx_cli(["install", PKG["black"]["spec"]])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade-all", *(["--include-injected"] if injected else [])])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert "upgraded package black from 22.8.0 to " in captured.out


def test_upgrade_all_reports_outdated_check_failure(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()
    check: Final[MagicMock] = mocker.patch(
        "pipx.backends.pip.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(
            args=["pip", "list"],
            returncode=1,
            stdout="",
            stderr="index unavailable",
        ),
    )

    assert run_pipx_cli(["upgrade-all"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (check.call_count, "Package backend exited with code 1" in captured.err) == (1, True)


def test_upgrade_all_skips_pinned_package_check(
    pipx_temp_env: None,
    caplog: pytest.LogCaptureFixture,
    mocker: MockerFixture,
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["pin", "pycowsay"])
    caplog.clear()
    check: Final[MagicMock] = mocker.patch(
        "pipx.backends.pip.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=["pip", "list"], returncode=0, stdout="[]", stderr=""),
    )

    assert (
        run_pipx_cli(["upgrade-all"]),
        check.call_count,
        "Not upgrading pinned package pycowsay" in caplog.text,
    ) == (0, 0, True)


def test_upgrade_all_quiet(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade-all", "--quiet"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert not captured.out
    assert not captured.err


def test_upgrade_all_json(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade-all", "--json"])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "pycowsay")
    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert not captured.err
    assert json.loads(captured.out) == {
        "command": ["upgrade-all"],
        "data": {
            "packages": [
                {
                    "environment": "pycowsay",
                    "injected": False,
                    "location": str(paths.ctx.venvs / "pycowsay"),
                    "package": "pycowsay",
                    "previous_version": "0.0.0.2",
                    "status": "unchanged",
                    "version": "0.0.0.2",
                    "interpreter": metadata.python_version,
                    "backend": metadata.backend,
                }
            ],
            "skipped": [],
        },
        "pipx_result_version": "1",
        "errors": [],
        "exit_code": 0,
        "status": "success",
    }


def test_upgrade_all_pylock_json(
    pipx_temp_env: None,
    make_pylock: Callable[[str, str], Path],
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    lock_file: Final[Path] = make_pylock("pycowsay", "0.0.0.2")
    assert not run_pipx_cli(["install", "--lock", str(lock_file), "pycowsay"])
    capsys.readouterr()
    check: Final[MagicMock] = mocker.patch(
        "pipx.backends.pip.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=["pip", "list"], returncode=0, stdout="[]", stderr=""),
    )

    assert not run_pipx_cli(["upgrade-all", "--json"])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.ctx.venvs / "pycowsay")
    assert (json.loads(capsys.readouterr().out)["data"]["packages"], check.call_count) == (
        [
            {
                "environment": "pycowsay",
                "injected": False,
                "location": str(paths.ctx.venvs / "pycowsay"),
                "package": "pycowsay",
                "previous_version": "0.0.0.2",
                "status": "locked",
                "version": "0.0.0.2",
                "interpreter": metadata.python_version,
                "backend": metadata.backend,
            }
        ],
        0,
    )


def test_upgrade_all_json_failure(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay")
    capsys.readouterr()

    assert run_pipx_cli(["upgrade-all", "--json"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert not captured.err
    assert json.loads(captured.out) == {
        "command": ["upgrade-all"],
        "data": {"packages": [], "skipped": []},
        "errors": [
            {
                "code": "package_upgrade_failed",
                "environment": "pycowsay",
                "message": (
                    "Not upgrading pycowsay. It has missing internal pipx metadata.\n"
                    "It was likely installed using a pipx version before 0.15.0.0.\n"
                    "Please uninstall and install this package to fix."
                ),
                "package": None,
            }
        ],
        "exit_code": 1,
        "pipx_result_version": "1",
        "status": "error",
    }


def test_upgrade_all_json_requested_skip(pipx_temp_env: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade-all", "--skip", "pycowsay", "--json"])

    assert json.loads(capsys.readouterr().out)["data"] == {
        "packages": [],
        "skipped": [{"environment": "pycowsay", "reason": "requested"}],
    }


def test_upgrade_all_json_editable_skip(pipx_temp_env: None, capsys: pytest.CaptureFixture[str], root: Path) -> None:
    assert not run_pipx_cli(["install", "--editable", str(root / "testdata" / "empty_project"), "--force"])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade-all", "--json"])

    assert json.loads(capsys.readouterr().out)["data"] == {
        "packages": [],
        "skipped": [{"environment": "empty-project", "reason": "editable"}],
    }


def test_upgrade_all_with_index_args(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    check: Final[MagicMock] = mocker.patch(
        "pipx.backends.pip.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=["pip", "list"], returncode=0, stdout="[]", stderr=""),
    )

    assert (
        run_pipx_cli(["upgrade-all", "--pip-args=--index-url=https://example.com"]),
        check.call_count,
        "--index-url=https://example.com" in check.call_args.args[0],
    ) == (0, 1, True)


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
def test_upgrade_all_legacy_venv(
    pipx_temp_env: None,
    capsys: pytest.CaptureFixture[str],
    metadata_version: str | None,
) -> None:
    assert run_pipx_cli(["upgrade", "pycowsay"])
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    if metadata_version is None:
        capsys.readouterr()
        assert run_pipx_cli(["upgrade-all"])
        assert "The following package(s) failed to upgrade: pycowsay" in capsys.readouterr().err
    else:
        assert not run_pipx_cli(["upgrade-all"])
