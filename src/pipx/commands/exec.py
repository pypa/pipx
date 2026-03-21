from pathlib import Path

from pipx.constants import EXIT_CODE_OK, WINDOWS, ExitCode
from pipx.util import PipxError
from pipx.venv import Venv


def exec_(package: str, app: str, app_args: list[str], venv_dir: Path, verbose: bool) -> ExitCode:
    """Execute an app from an existing pipx-managed virtual environment."""
    venv = Venv(venv_dir, verbose=verbose)
    if not venv.python_path.exists():
        raise PipxError(f"venv for {package!r} was not found. Was {package!r} installed with pipx?")

    if WINDOWS:
        app_filename = f"{app}.exe"
    else:
        app_filename = app

    if not venv.has_app(app, app_filename):
        raise PipxError(f"App '{app}' not found in pipx package '{package}'.")

    venv.run_app(app, app_filename, app_args)

    return EXIT_CODE_OK
