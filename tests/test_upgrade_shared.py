from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Final

import pytest

from helpers import run_pipx_cli
from pipx import shared_libs as shared_libs_module

if TYPE_CHECKING:
    from pipx.shared_libs import _SharedLibs  # fixture returns the private singleton, no public type


def test_upgrade_shared_creates_and_upgrades(
    shared_libs: _SharedLibs, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    assert (shared_libs.has_been_updated_this_run, shared_libs.is_valid) == (False, False)

    assert run_pipx_cli(["upgrade-shared", "-v"]) == 0

    err: Final[str] = capsys.readouterr().err
    assert (
        "creating shared libraries" in err,
        "upgrading shared libraries" in err,
        "Upgrading shared libraries in" in caplog.text,
        "Already upgraded libraries in" in caplog.text,
        shared_libs.has_been_updated_this_run,
        shared_libs.is_valid,
    ) == (True, True, True, False, True, True)


@pytest.fixture
def shared_libs(pipx_ultra_temp_env: None) -> _SharedLibs:  # ruff:ignore[unused-function-argument]  # required fixture dependency; usefixtures has no effect on fixtures
    # read after pipx_ultra_temp_env replaced the module's instance with a fresh one
    return shared_libs_module.SHARED_LIBS


def test_upgrade_shared_upgrades_existing_without_creating(
    shared_libs: _SharedLibs, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    assert run_pipx_cli(["upgrade-shared", "-v"]) == 0
    shared_libs.has_been_updated_this_run = False
    capsys.readouterr()
    caplog.clear()

    assert run_pipx_cli(["upgrade-shared", "-v"]) == 0

    err: Final[str] = capsys.readouterr().err
    assert (
        "creating shared libraries" in err,
        "upgrading shared libraries" in err,
        "Upgrading shared libraries in" in caplog.text,
        "Already upgraded libraries in" in caplog.text,
        shared_libs.has_been_updated_this_run,
    ) == (False, True, True, False, True)


@pytest.mark.usefixtures("shared_libs")
def test_upgrade_shared_skips_libraries_upgraded_this_run(caplog: pytest.LogCaptureFixture) -> None:
    assert run_pipx_cli(["upgrade-shared", "-v"]) == 0

    assert run_pipx_cli(["upgrade-shared", "-v"]) == 0

    assert "Already upgraded libraries in" in caplog.text


def test_upgrade_shared_pip_args(
    shared_libs: _SharedLibs, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    assert (shared_libs.has_been_updated_this_run, shared_libs.is_valid) == (False, False)

    exit_code: Final[int] = run_pipx_cli(["upgrade-shared", "-v", "--pip-args='--no-index'"])

    err: Final[str] = capsys.readouterr().err
    assert (
        exit_code,
        "creating shared libraries" in err,
        "upgrading shared libraries" in err,
        "Upgrading shared libraries in" in caplog.text,
        "Already upgraded libraries in" in caplog.text,
        shared_libs.has_been_updated_this_run,
        shared_libs.is_valid,
    ) == (1, True, True, True, False, False, True)


def test_upgrade_shared_pin_pip(shared_libs: _SharedLibs) -> None:
    # Pin to a version testdata/tests_packages/primary_packages.txt seeds explicitly: it clears the `pip >= 26.2.2`
    # floor upgrade-shared appends yet stays behind the latest, so a bare `pip` entry alone would drop it once pip
    # moves on. The assertion then proves --pip-args placed it rather than matching the default upgrade.
    pinned: Final[str] = "26.2.2"
    assert (shared_libs.has_been_updated_this_run, shared_libs.is_valid) == (False, False)

    assert run_pipx_cli(["upgrade-shared", "-v", f"--pip-args=pip=={pinned}"]) == 0

    assert (
        shared_libs.is_valid,
        subprocess.run(
            [shared_libs.python_path, "-c", "from importlib.metadata import version; print(version('pip'))"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
    ) == (True, pinned)
