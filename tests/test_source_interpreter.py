from __future__ import annotations

import sys
import venv
from typing import TYPE_CHECKING, Final

import pytest

from helpers import run_pipx_cli
from package_info import PKG
from pipx import paths
from pipx.interpreter import recordable_interpreter
from pipx.pipx_metadata_file import PipxMetadata
from pipx.util import get_venv_paths

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "symlinks",
    [
        pytest.param(
            True, id="symlinks", marks=pytest.mark.skipif(sys.platform == "win32", reason="venv copies on Windows")
        ),
        pytest.param(False, id="copies"),
    ],
)
@pytest.mark.usefixtures("pipx_temp_env")
def test_install_from_bootstrap_venv_records_interpreter_outside_it(tmp_path: Path, symlinks: bool) -> None:
    venv.create(bootstrap := tmp_path / "bootstrap", symlinks=symlinks)
    _, bootstrap_python, _ = get_venv_paths(bootstrap)

    assert not run_pipx_cli(["install", "--python", str(bootstrap_python), PKG["pycowsay"]["spec"]])

    recorded: Final[Path | None] = PipxMetadata(paths.CTX.venvs / "pycowsay").source_interpreter
    assert recorded is not None
    assert (recorded.is_file(), recorded.is_relative_to(bootstrap)) == (True, False)


@pytest.mark.parametrize(
    "pyvenv_cfg",
    [
        pytest.param(b"home = {missing}\n", id="home-without-interpreter"),
        pytest.param(b"version = 3.14.0\n", id="no-home"),
        pytest.param(b"home = \xff\n", id="undecodable"),
    ],
)
def test_recordable_interpreter_without_base_interpreter_is_none(tmp_path: Path, pyvenv_cfg: bytes) -> None:
    (bootstrap := tmp_path / "bootstrap").mkdir()
    (bootstrap / "pyvenv.cfg").write_bytes(pyvenv_cfg.replace(b"{missing}", str(tmp_path / "missing").encode()))
    (bin_dir := bootstrap / "bin").mkdir()
    (python := bin_dir / "python3").touch()

    assert recordable_interpreter(python) is None
