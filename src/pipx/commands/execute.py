from __future__ import annotations

__lazy_modules__ = ["itertools", "pipx.subprocess_runner", "pipx.util", "pipx.venv"]

import os
from itertools import chain
from typing import TYPE_CHECKING, Final, NoReturn

from pipx.constants import WINDOWS
from pipx.subprocess_runner import exec_app
from pipx.util import PipxError
from pipx.venv import Venv

if TYPE_CHECKING:
    from pathlib import Path


def execute(package: str, venv_dir: Path, app: str, app_args: list[str]) -> NoReturn:
    if not venv_dir.is_dir():
        msg = f"pipx does not manage environment {package!r}."
        raise PipxError(msg)

    venv: Final[Venv] = Venv(venv_dir)
    app_paths: Final[dict[str, Path]] = _application_paths(venv)
    if (app_path := app_paths.get(app)) is None:
        available: Final[str] = ", ".join(sorted(app_paths)) or "none"
        msg = f"Application {app!r} was not found in environment {package!r}.\nAvailable applications: {available}"
        raise PipxError(msg, wrap_message=False)
    if not app_path.is_file():
        msg = (
            f"Application {app!r} is missing from environment {package!r} at {app_path}.\n"
            f"Reinstall it with `pipx reinstall {package}`."
        )
        raise PipxError(msg, wrap_message=False)

    environment: Final[dict[str, str]] = dict(os.environ)
    environment["VIRTUAL_ENV"] = str(venv_dir)
    environment["PATH"] = (
        os.pathsep.join((str(venv.bin_path), path)) if (path := environment.get("PATH")) else str(venv.bin_path)
    )
    exec_app([app_path, *app_args], env=environment)


def _application_paths(venv: Venv) -> dict[str, Path]:
    return {
        path.stem if WINDOWS and path.suffix.lower() == ".exe" else path.name: path
        for package in (venv.pipx_metadata.main_package, *venv.pipx_metadata.injected_packages.values())
        for path in chain(package.app_paths, *package.app_paths_of_dependencies.values())
    }


__all__ = [
    "execute",
]
