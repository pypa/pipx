from __future__ import annotations

import json
import logging
import os
import re
import shutil
import signal
import subprocess
import time
from threading import Barrier
from typing import TYPE_CHECKING, Final, ParamSpec, TypeVar

import pytest

from helpers import (
    PIPX_METADATA_LEGACY_VERSIONS,
    SKIP_IF_WINDOWS,
    mock_legacy_venv,
    remove_venv_interpreter,
    run_pipx_cli,
)
from package_info import PKG
from pipx import paths
from pipx.constants import EXIT_CODE_LIST_PROBLEM
from pipx.pipx_metadata_file import PIPX_INFO_FILENAME, PipxMetadata

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path
    from unittest.mock import MagicMock

    from _pytest.capture import CaptureResult
    from pytest_mock import MockerFixture


_P = ParamSpec("_P")
_R = TypeVar("_R")


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all() -> None:
    assert run_pipx_cli(["upgrade", "pycowsay"])
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["upgrade-all"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_none(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])

    assert not run_pipx_cli(["upgrade-all"])

    assert "No packages upgraded after running 'pipx upgrade-all'" in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_warns_system_site_packages_is_ignored(caplog: pytest.LogCaptureFixture) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])

    assert not run_pipx_cli(["upgrade-all", "--system-site-packages"])

    assert any(
        record.levelno == logging.WARNING and "Ignoring --system-site-packages" in record.getMessage()
        for record in caplog.records
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_checks_current_packages_concurrently(
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    for suffix in ("_one", "_two", "_three"):
        assert not run_pipx_cli(["install", "pycowsay", f"--suffix={suffix}"])
    capsys.readouterr()
    barrier: Final[Barrier] = Barrier(3)

    def check_package(
        cmd: Sequence[str | Path],
        *,
        capture_stdout: bool = True,
        capture_stderr: bool = True,
        log_cmd_str: str | None = None,
        log_stdout: bool = True,
        log_stderr: bool = True,
        run_dir: str | None = None,
        env_overrides: dict[str, str | None] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del capture_stdout, capture_stderr, log_cmd_str, log_stdout, log_stderr, run_dir, env_overrides
        assert "list" in cmd
        assert "--outdated" in cmd
        barrier.wait(timeout=5)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="[]", stderr="")

    check: Final[MagicMock] = mocker.patch("pipx.backends.pip.run_subprocess", autospec=True, side_effect=check_package)

    assert (run_pipx_cli(["upgrade-all"]), check.call_count) == (0, 3)


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_does_not_copy_current_environment(
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


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_updates_current_cooldowns(
    package_cache_dir: Path,
    mocker: MockerFixture,
) -> None:
    pip_args: Final[str] = f"--pip-args=--no-index --find-links={package_cache_dir}"
    assert not run_pipx_cli(["install", "--cooldown", "7", pip_args, PKG["pycowsay"]["spec"]])
    assert not run_pipx_cli(["inject", "--cooldown", "5", pip_args, "pycowsay", PKG["black"]["spec"]])
    mocker.patch(
        "pipx.backends.pip.run_subprocess",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=["pip", "list"], returncode=0, stdout="[]", stderr=""),
    )

    assert not run_pipx_cli(["upgrade-all", "--include-injected", "--cooldown", "0"])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "pycowsay")
    assert (metadata.main_package.cooldown_days, metadata.injected_packages["black"].cooldown_days) == (0, 0)


@pytest.mark.parametrize(
    ("setup_commands", "flags"),
    [
        pytest.param([["install", PKG["black"]["spec"]]], [], id="main"),
        pytest.param(
            [["install", "pycowsay"], ["inject", "pycowsay", PKG["black"]["spec"]]],
            ["--include-injected"],
            id="injected",
        ),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_upgrades_outdated_package(
    capsys: pytest.CaptureFixture[str], setup_commands: list[list[str]], flags: list[str]
) -> None:
    for command in setup_commands:
        assert not run_pipx_cli(command)
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade-all", *flags])

    assert "upgraded package black from 22.8.0 to " in capsys.readouterr().out


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_reports_outdated_check_failure(
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


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_skips_pinned_package_check(
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


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_quiet(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade-all", "--quiet"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade-all", "--output", "json"])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "pycowsay")
    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["upgrade-all"],
            "data": {
                "packages": [
                    {
                        "environment": "pycowsay",
                        "injected": False,
                        "location": str(paths.CTX.venvs / "pycowsay"),
                        "package": "pycowsay",
                        "previous_version": "0.0.0.2",
                        "status": "unchanged",
                        "version": "0.0.0.2",
                        "interpreter": metadata.python_version,
                        "backend": metadata.backend,
                        "source": None,
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


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_pylock_json(
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

    assert not run_pipx_cli(["upgrade-all", "--output", "json"])

    metadata: Final[PipxMetadata] = PipxMetadata(paths.CTX.venvs / "pycowsay")
    assert (json.loads(capsys.readouterr().out)["data"]["packages"], check.call_count) == (
        [
            {
                "environment": "pycowsay",
                "injected": False,
                "location": str(paths.CTX.venvs / "pycowsay"),
                "package": "pycowsay",
                "previous_version": "0.0.0.2",
                "status": "locked",
                "version": "0.0.0.2",
                "interpreter": metadata.python_version,
                "backend": metadata.backend,
                "source": None,
            }
        ],
        0,
    )


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_json_failure(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay")
    capsys.readouterr()

    assert run_pipx_cli(["upgrade-all", "--output", "json"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (json.loads(captured.out), captured.err) == (
        {
            "command": ["upgrade-all"],
            "data": {"packages": [], "skipped": []},
            "errors": [
                {
                    "code": "package_upgrade_failed",
                    "environment": "pycowsay",
                    "message": (
                        "Not upgrading pycowsay. It has no internal pipx metadata.\n"
                        "pipx versions before 0.15.0.0 did not record it.\n"
                        "Uninstall and install this package to fix it."
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


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_json_requested_skip(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade-all", "--skip", "pycowsay", "--output", "json"])

    assert json.loads(capsys.readouterr().out)["data"] == {
        "packages": [],
        "skipped": [{"environment": "pycowsay", "reason": "requested"}],
    }


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_json_editable_skip(capsys: pytest.CaptureFixture[str], empty_project: Path) -> None:
    assert not run_pipx_cli(["install", "--editable", str(empty_project), "--force"])
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade-all", "--output", "json"])

    assert json.loads(capsys.readouterr().out)["data"] == {
        "packages": [],
        "skipped": [{"environment": "empty-project", "reason": "editable"}],
    }


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_with_index_args(mocker: MockerFixture) -> None:
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


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_legacy_venv_without_metadata_fails(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["upgrade", "pycowsay"])
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=None)
    capsys.readouterr()

    assert run_pipx_cli(["upgrade-all"])

    assert "The following package(s) failed to upgrade: pycowsay" in capsys.readouterr().err


@pytest.mark.parametrize(
    "metadata_version", [version for version in PIPX_METADATA_LEGACY_VERSIONS if version is not None]
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_legacy_venv(metadata_version: str) -> None:
    assert run_pipx_cli(["upgrade", "pycowsay"])
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)

    assert not run_pipx_cli(["upgrade-all"])


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_prints_progress_in_venv_order(
    capsys: pytest.CaptureFixture[str], mocker: MockerFixture, outdated_venv_names: list[str]
) -> None:
    slow: Final[Path] = paths.CTX.venvs / outdated_venv_names[0]

    # the backup of an environment with expected apps precedes its upgrade progress line
    def backup(source: Path, destination: Path, *, symlinks: bool) -> Path:
        if source == slow:
            time.sleep(0.3)
        return shutil.copytree(source, destination, symlinks=symlinks)

    mocker.patch("pipx.commands.transaction.copytree", side_effect=backup)

    assert not run_pipx_cli(["upgrade-all"])

    assert re.findall(r"^upgrading ([\w-]+)", capsys.readouterr().err, re.MULTILINE) == outdated_venv_names


@pytest.fixture
def outdated_venv_names(capsys: pytest.CaptureFixture[str]) -> list[str]:
    for app, spec in (("black", PKG["black"]["spec"]), ("isort", PKG["isort"]["spec"])):
        assert not run_pipx_cli(["install", "--app", app, spec])
    capsys.readouterr()
    return [venv_dir.name for venv_dir in paths.CTX.venvs.iterdir() if venv_dir.is_dir()]


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_upgrades_the_rest_after_a_failure(
    capsys: pytest.CaptureFixture[str], outdated_venv_names: list[str]
) -> None:
    mock_legacy_venv(outdated_venv_names[0])

    exit_code: Final[int] = run_pipx_cli(["upgrade-all", "--output", "json"])

    result: Final = json.loads(capsys.readouterr().out)
    assert (
        exit_code,
        [package["environment"] for package in result["data"]["packages"]],
        [error["environment"] for error in result["errors"]],
    ) == (1, outdated_venv_names[1:], outdated_venv_names[:1])


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_upgrades_the_rest_after_a_missing_interpreter(
    capsys: pytest.CaptureFixture[str], outdated_venv_names: list[str]
) -> None:
    remove_venv_interpreter(outdated_venv_names[0])

    exit_code: Final[int] = run_pipx_cli(["upgrade-all"])

    captured: Final[CaptureResult[str]] = capsys.readouterr()
    assert (
        exit_code,
        f"upgraded package {outdated_venv_names[1]} from " in captured.out,
        f"Not upgrading {outdated_venv_names[0]}. It has an invalid python interpreter" in captured.err,
        f"The following package(s) failed to upgrade: {outdated_venv_names[0]}" in captured.err,
    ) == (1, True, True, True)


@pytest.mark.usefixtures("pipx_temp_env")
def test_upgrade_all_upgrades_beside_corrupt_metadata(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["install", PKG["black"]["spec"]])
    metadata_file: Final[Path] = paths.CTX.venvs / "pycowsay" / PIPX_INFO_FILENAME
    metadata: Final = json.loads(metadata_file.read_text(encoding="utf-8"))
    metadata["main_package"]["app_paths"] = None
    metadata_file.write_text(json.dumps(metadata), encoding="utf-8")
    capsys.readouterr()

    assert not run_pipx_cli(["upgrade-all", "--output", "json"])

    assert {
        package["environment"]: package["status"] for package in json.loads(capsys.readouterr().out)["data"]["packages"]
    } == {"black": "upgraded", "pycowsay": "unchanged"}


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env", "signal_handlers", "black_installed")
def test_upgrade_all_finishes_upgrade_in_progress_on_first_interrupt(
    capsys: pytest.CaptureFixture[str], interrupt_upgrade: Callable[[int], None]
) -> None:
    interrupt_upgrade(1)

    exit_code: Final[int] = run_pipx_cli(["upgrade-all"])

    assert (exit_code, "upgraded package black from 22.8.0 to " in capsys.readouterr().out) == (1, True)


@pytest.fixture
def interrupt_upgrade(mocker: MockerFixture, caplog: pytest.LogCaptureFixture) -> Callable[[int], None]:
    # signal pipx alone as pip starts upgrading the first black venv, as pressing Ctrl-C that many times would
    def patch(presses: int) -> None:
        mocker.patch.object(subprocess, "Popen", side_effect=_interrupting(subprocess.Popen, presses, caplog))

    return patch


def _interrupting(call: Callable[_P, _R], presses: int, caplog: pytest.LogCaptureFixture) -> Callable[_P, _R]:
    pending: Final[list[int]] = [presses]

    def interrupting(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        if pending[0] and "--upgrade" in (command := str(args[0])) and f"{os.sep}black" in command:
            for press in range(pending.pop()):
                os.kill(os.getpid(), signal.SIGINT)
                deadline: Final[float] = time.monotonic() + 5
                while press == 0 and not any("Finishing" in message for message in caplog.messages):
                    if time.monotonic() > deadline:
                        break
                    time.sleep(0.01)
            pending.append(0)
        return call(*args, **kwargs)

    return interrupting


@pytest.fixture
def black_installed(capsys: pytest.CaptureFixture[str]) -> None:
    assert not run_pipx_cli(["install", PKG["black"]["spec"]])
    capsys.readouterr()


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env", "signal_handlers", "black_installed")
def test_upgrade_all_reports_upgrade_stopped_by_second_interrupt(
    capsys: pytest.CaptureFixture[str], interrupt_upgrade: Callable[[int], None]
) -> None:
    interrupt_upgrade(2)

    exit_code: Final[int] = run_pipx_cli(["upgrade-all"])

    assert (exit_code, "Interrupted while upgrading black;" in capsys.readouterr().err) == (1, True)


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env", "signal_handlers", "black_installed")
def test_upgrade_all_does_not_start_upgrades_after_interrupt(
    capsys: pytest.CaptureFixture[str], mocker: MockerFixture, interrupt_upgrade: Callable[[int], None]
) -> None:
    assert not run_pipx_cli(["install", PKG["black"]["spec"], "--suffix=_x"])
    capsys.readouterr()
    # one worker, so the upgrade of the other venv waits for the interrupted one
    mocker.patch.object(os, "cpu_count", return_value=1)
    interrupt_upgrade(1)

    exit_code: Final[int] = run_pipx_cli(["upgrade-all"])

    assert (exit_code, "Interrupted before upgrading: black" in capsys.readouterr().err) == (1, True)


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env", "signal_handlers", "black_installed", "unfinished_black")
def test_list_reports_venv_left_unfinished_by_interrupt(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code: Final[int] = run_pipx_cli(["list"])

    assert (exit_code, "left half changed by an interrupted pipx run: black." in capsys.readouterr().err) == (
        EXIT_CODE_LIST_PROBLEM,
        True,
    )


@pytest.fixture
def unfinished_black(capsys: pytest.CaptureFixture[str], interrupt_upgrade: Callable[[int], None]) -> None:
    interrupt_upgrade(2)
    assert run_pipx_cli(["upgrade-all"])
    capsys.readouterr()


@SKIP_IF_WINDOWS
@pytest.mark.parametrize(
    "command",
    [
        pytest.param(["upgrade-all"], id="upgrade-all"),
        pytest.param(["upgrade", "black"], id="upgrade"),
        pytest.param(["reinstall", "black"], id="reinstall"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env", "signal_handlers", "black_installed", "unfinished_black")
def test_command_repairs_venv_left_unfinished_by_interrupt(
    capsys: pytest.CaptureFixture[str], command: list[str]
) -> None:
    assert not run_pipx_cli(command)
    capsys.readouterr()

    assert (run_pipx_cli(["list"]), "interrupted" in capsys.readouterr().err) == (0, False)


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("pipx_temp_env", "signal_handlers", "black_installed", "unfinished_black")
def test_upgrade_all_repairs_unfinished_venv_whose_python_is_gone(capsys: pytest.CaptureFixture[str]) -> None:
    remove_venv_interpreter("black")

    assert not run_pipx_cli(["upgrade-all"])
    capsys.readouterr()

    assert (run_pipx_cli(["list"]), "interrupted" in capsys.readouterr().err) == (0, False)
