from __future__ import annotations

import importlib
import os
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

import pipx.commands

if TYPE_CHECKING:
    from pathlib import Path


def test_importing_util_first_succeeds(root: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(root / "src")}

    result = subprocess.run(
        [sys.executable, "-c", "import pipx.util; print('Success!')"],
        check=False,
        capture_output=True,
        cwd=root,
        env=env,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "Success!\n"


@pytest.mark.parametrize(
    "module",
    [
        pytest.param("filelock", id="filelock"),
        pytest.param("logging.config", id="logging-config"),
        pytest.param("packaging.requirements", id="packaging-requirements"),
        pytest.param("importlib.metadata", id="importlib-metadata"),
        pytest.param("pipx.venv_inspect", id="venv-inspect"),
        pytest.param("zipfile", id="zipfile"),
        pytest.param("hashlib", id="hashlib"),
        pytest.param("urllib.request", id="urllib-request"),
        pytest.param("pipx.standalone_python", id="standalone-python"),
        pytest.param("pipx.commands.install", id="command-module"),
    ],
)
def test_importing_main_defers_heavy_module(root: Path, module: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", f"import sys, pipx.main; print({module!r} in sys.modules)"],
        check=False,
        capture_output=True,
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
        text=True,
    )

    assert result.stdout == "False\n", result.stderr


def test_commands_package_resolves_reexport_from_submodule() -> None:
    assert pipx.commands.install_all is importlib.import_module("pipx.commands.install").install_all


def test_commands_package_rejects_unknown_attribute() -> None:
    with pytest.raises(AttributeError, match="has no attribute 'missing'"):
        _ = pipx.commands.missing
