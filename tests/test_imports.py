from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

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
        pytest.param("urllib.request", id="urllib-request"),
        pytest.param("pipx.standalone_python", id="standalone-python"),
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
