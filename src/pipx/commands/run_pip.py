from pathlib import Path
from typing import List

from pipx.util import PipxError
from pipx.venv import Venv


def run_pip(package: str, venv_dir: Path, pip_args: List[str], verbose: bool) -> int:
    venv = Venv(venv_dir, verbose=verbose)
    if not venv.python_path.exists():
        raise PipxError(
            f"venv for {package!r} was not found. Was {package!r} installed with pipx?"
        )
    venv.verbose = True
    venv._run_pip(pip_args)

    # TODO: verify
    # TODO: venv._run_pip() will raise PipxError for any non-zero pip error code
    #   but we should return actual pip error code
    return 0
