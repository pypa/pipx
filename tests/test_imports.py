from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

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
