import os
import subprocess
import sys


def test_importing_util_first_succeeds(root):
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
