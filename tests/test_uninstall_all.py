from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from helpers import PIPX_METADATA_LEGACY_VERSIONS, mock_legacy_venv, run_pipx_cli, skip_if_windows, write_wheel
from pipx import paths
from pipx.commands import uninstall as uninstall_module
from pipx.util import rmdir_via_trash

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


@pytest.mark.usefixtures("pipx_temp_env", "capsys")
def test_uninstall_all() -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    assert not run_pipx_cli(["uninstall-all"])


@pytest.mark.parametrize("metadata_version", PIPX_METADATA_LEGACY_VERSIONS)
@pytest.mark.usefixtures("pipx_temp_env", "capsys")
def test_uninstall_all_legacy_venv(metadata_version: str | None) -> None:
    assert not run_pipx_cli(["install", "pycowsay"])
    mock_legacy_venv("pycowsay", metadata_version=metadata_version)
    assert not run_pipx_cli(["uninstall-all"])


@skip_if_windows
@pytest.mark.usefixtures("pipx_temp_env")
def test_uninstall_all_keeps_an_app_name_taken_over_while_it_runs(mocker: MockerFixture, tmp_path: Path) -> None:
    assert not run_pipx_cli(["install", str(write_wheel(tmp_path / "wheels", "alpha", "1"))])
    assert not run_pipx_cli(["install", str(write_wheel(tmp_path / "wheels", "beta", "1"))])
    (other := tmp_path / "other").touch()

    def remove_then_take_over_the_remaining_names(path: Path) -> None:
        # uninstall-all scans the bin directory once, so the later venvs act on what it held before this takeover
        rmdir_via_trash(path)
        for name in {"alpha", "beta"} & {entry.name for entry in paths.ctx.venvs.iterdir()}:
            (app := paths.ctx.bin_dir / name).unlink()
            app.symlink_to(other)

    mocker.patch.object(
        uninstall_module, "rmdir_via_trash", autospec=True, side_effect=remove_then_take_over_the_remaining_names
    )

    assert not run_pipx_cli(["uninstall-all"])

    assert [path.resolve() for path in paths.ctx.bin_dir.iterdir()] == [other.resolve()]
