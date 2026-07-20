from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from helpers import run_pipx_cli, skip_if_windows
from pipx import paths
from pipx.commands import common
from pipx.commands.common import (
    _remove_stale_venv_resources,  # ruff:ignore[import-private-name]  # test exercises private helper, no public API
    expose_resources_globally,
    get_exposed_paths_for_package,
)
from pipx.venv import Venv

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


@skip_if_windows
def test_get_exposed_paths_ignores_recursive_symlink(tmp_path: Path) -> None:
    venv_resource_path = tmp_path / "venv_bin"
    venv_resource_path.mkdir()
    local_resource_dir = tmp_path / "bin"
    local_resource_dir.mkdir()
    loop = local_resource_dir / "recursiveexample"
    loop.symlink_to(loop.name)

    exposed = get_exposed_paths_for_package(venv_resource_path, local_resource_dir)

    assert loop not in exposed


@skip_if_windows
def test_expose_app_scripts_ignores_pythonpath(tmp_path: Path) -> None:
    venv_resource_path = tmp_path / "venv_bin"
    venv_resource_path.mkdir()
    local_resource_dir = tmp_path / "bin"
    shadow_path = tmp_path / "shadow"
    shadow_path.mkdir()

    app_path = venv_resource_path / "demo"
    app_path.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        f"if {str(shadow_path)!r} in sys.path:\n"
        "    raise SystemExit('PYTHONPATH leaked into app script')\n"
        "print('ok')\n"
    )
    app_path.chmod(0o755)

    expose_resources_globally("app", local_resource_dir, [app_path], force=False)

    assert app_path.read_text().splitlines()[0] == f"#!{sys.executable} -E"

    result = subprocess.run(
        [app_path],
        check=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(shadow_path)},
        text=True,
    )
    assert result.stdout == "ok\n"


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env")
def test_remove_stale_venv_resources_keeps_files_pipx_does_not_own(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_pipx_cli(["install", "pycowsay"]) == 0
    capsys.readouterr()
    venv = Venv(paths.ctx.venvs / "pycowsay")
    bin_dir = paths.ctx.bin_dir

    owned = bin_dir / "stale-owned"
    owned.symlink_to(venv.pipx_metadata.main_package.app_paths[0])
    replaced = bin_dir / "stale-replaced"
    replaced.write_text("belongs to the user")

    _remove_stale_venv_resources({owned, replaced}, venv, bin_dir, paths.ctx.man_dir)

    assert (owned.exists(), replaced.read_text()) == (False, "belongs to the user")


# A binary pipx did not create is parsed as if it were a launcher, so the bytes trailing a stray "#!" reach
# os.fsdecode and stat as an interpreter path. Windows rejects the undecodable one, every platform the NUL.
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(b"MZ\x90\x00\x03#!\xff\xfe\x80\x81 more binary\n", id="undecodable-interpreter"),
        pytest.param(b"MZ\x90\x00\x03#!/opt/no\x00pe/bin/python\n", id="nul-in-interpreter"),
    ],
)
def test_get_exposed_paths_ignores_foreign_binary(tmp_path: Path, mocker: MockerFixture, payload: bytes) -> None:
    # Only copy-based environments read a shebang to establish ownership, so without this the symlink branch
    # short-circuits the scan and the parse under test never runs off Windows.
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=False)
    venv_resource_path = tmp_path / "venv_bin"
    venv_resource_path.mkdir()
    local_resource_dir = tmp_path / "bin"
    local_resource_dir.mkdir()
    foreign = local_resource_dir / "foreign.exe"
    foreign.write_bytes(payload)

    exposed = get_exposed_paths_for_package(venv_resource_path, local_resource_dir)

    assert foreign not in exposed


@pytest.mark.parametrize(
    "owned",
    [pytest.param(True, id="shebang-into-venv"), pytest.param(False, id="shebang-elsewhere")],
)
def test_get_exposed_paths_matches_copied_launcher(tmp_path: Path, mocker: MockerFixture, owned: bool) -> None:
    mocker.patch.object(common, "can_symlink", autospec=True, return_value=False)
    venv_resource_path = tmp_path / "venv_bin"
    venv_resource_path.mkdir()
    local_resource_dir = tmp_path / "bin"
    local_resource_dir.mkdir()
    elsewhere = tmp_path / "other"
    elsewhere.mkdir()
    launcher = local_resource_dir / "myapp"
    launcher.write_text(f"#!{(venv_resource_path if owned else elsewhere) / 'python'}\n")

    exposed = get_exposed_paths_for_package(venv_resource_path, local_resource_dir)

    assert (launcher in exposed) is owned
