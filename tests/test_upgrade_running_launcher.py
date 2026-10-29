from __future__ import annotations

import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, Final

import pytest

from helpers import SKIP_IF_WINDOWS, WIN, app_name, run_pipx_cli, write_wheel
from pipx import paths
from pipx.backends import uv as uv_backend
from pipx.main import cli
from pipx.util import get_venv_paths

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from pytest_mock import MockerFixture

pytestmark = pytest.mark.skipif(shutil.which("uv") is None, reason="uv binary not on PATH")


@pytest.fixture
def index(
    pipx_temp_env: None,  # ruff:ignore[unused-function-argument]  # the temp env must be active while installing
    tmp_path: Path,
) -> Path:
    index: Final[Path] = tmp_path / "index"
    # the app waits for its input to close, so a launcher started with a pipe stays running
    write_wheel(index, "tool", "1.0", module_code="import sys\n\nsys.stdin.read()\nsys.exit()\n")
    assert not run_pipx_cli(["install", "--backend", "uv", f"--pip-args=--no-index --find-links {index}", "tool"])
    return index


@pytest.fixture
def launcher(index: Path) -> Path:  # ruff:ignore[unused-function-argument]  # the tool must be installed first
    return get_venv_paths(paths.CTX.venvs / "tool")[0] / app_name("tool")


@pytest.fixture
def read_only_trash() -> Iterator[None]:
    (trash := paths.CTX.trash).mkdir(parents=True, exist_ok=True)
    trash.chmod(0o500)
    yield
    trash.chmod(0o700)


@pytest.mark.skipif(not WIN, reason="only Windows refuses to delete a running launcher")
def test_upgrade_uv_replaces_the_running_launcher(index: Path, launcher: Path, mocker: MockerFixture) -> None:
    write_wheel(index, "tool", "2.0")

    with subprocess.Popen([launcher], stdin=subprocess.PIPE):
        exit_code: Final[int] = _upgrade_started_from(launcher, mocker)

    assert (exit_code, _installed_versions()) == (0, ["tool-2.0.dist-info"])


def test_upgrade_uv_puts_back_the_launcher_it_did_not_replace(launcher: Path, mocker: MockerFixture) -> None:
    mocker.patch.object(uv_backend, "WINDOWS", True)
    content: Final[bytes] = launcher.read_bytes()

    assert not _upgrade_started_from(launcher, mocker)

    assert launcher.read_bytes() == content


@SKIP_IF_WINDOWS
@pytest.mark.usefixtures("read_only_trash")
def test_upgrade_uv_keeps_the_launcher_in_place_without_a_trash(
    index: Path, launcher: Path, mocker: MockerFixture
) -> None:
    mocker.patch.object(uv_backend, "WINDOWS", True)
    write_wheel(index, "tool", "2.0")

    assert (_upgrade_started_from(launcher, mocker), _installed_versions()) == (0, ["tool-2.0.dist-info"])


def _upgrade_started_from(launcher: Path, mocker: MockerFixture) -> int:
    # the Windows launcher names itself to Python without its .exe suffix
    mocker.patch.object(sys, "argv", [str(launcher.with_suffix("")), "upgrade", "tool"])
    return cli()


def _installed_versions() -> list[str]:
    return sorted(path.name for path in (paths.CTX.venvs / "tool").rglob("tool-*.dist-info"))
