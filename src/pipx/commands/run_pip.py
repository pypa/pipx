from pathlib import Path
from typing import List

from pipx import constants, shared_libs
from pipx.constants import ExitCode
from pipx.util import PipxError
from pipx.venv import Venv


def run_pip(
    package: str, venv_dir: Path, pip_args: List[str], verbose: bool
) -> ExitCode:
    """Returns pipx exit code."""
    venv = Venv(venv_dir, verbose=verbose)
    shared = venv_dir == constants.PIPX_SHARED_LIBS
    if shared:
        shared_libs.shared_libs.create()
        pip_args = [package] + pip_args
    if not venv.python_path.exists():
        raise PipxError(
            "shared venv could not be created or is in an invalid state"
            if shared
            else f"venv for {package!r} was not found. Was {package!r} installed with pipx?"
        )
    venv.verbose = True
    return venv.run_pip_get_exit_code(pip_args)
