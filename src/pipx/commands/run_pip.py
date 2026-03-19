from pathlib import Path

from pipx.constants import ExitCode
from pipx.util import PipxError
from pipx.venv import Venv


def run_pip(package: str, venv_dir: Path, pip_args: list[str], verbose: bool) -> ExitCode:
    """Returns pipx exit code."""
    venv = Venv(venv_dir, verbose=verbose)
    if not venv.python_path.exists():
        raise PipxError(f"venv for {package!r} was not found. Was {package!r} installed with pipx?")
    venv.verbose = True
    return venv.run_pip_get_exit_code(pip_args)
