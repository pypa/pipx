from pathlib import Path
from typing import List

from pipx.venv import Venv
from pipx.util import PipxError


def run_pip(package: str, venv_dir: Path, pip_args: List[str], verbose: bool):
    venv = Venv(venv_dir, verbose=verbose)
    if not venv.python_path.exists():
        raise PipxError(
            f"venv for {package!r} was not found. Was {package!r} installed with pipx?"
        )
    venv.verbose = True
    venv._run_pip(pip_args)
