from __future__ import annotations

import os
from itertools import chain
from typing import TYPE_CHECKING, Final, NoReturn

from pipx.constants import WINDOWS
from pipx.util import PipxError, exec_app
from pipx.venv import Venv

if TYPE_CHECKING:
    from pathlib import Path

    from pipx.pipx_metadata_file import PackageInfo


def execute(package: str, venv_dir: Path, app: str, app_args: list[str]) -> NoReturn:
    if not venv_dir.is_dir():
        raise PipxError(f"pipx does not manage environment {package!r}.")

    venv: Final[Venv] = Venv(venv_dir)
    app_paths: Final[dict[str, Path]] = _application_paths(venv)
    if (app_path := app_paths.get(app)) is None:
        available: Final[str] = ", ".join(sorted(app_paths)) or "none"
        raise PipxError(
            f"Application {app!r} was not found in environment {package!r}.\nAvailable applications: {available}",
            wrap_message=False,
        )
    if not app_path.is_file():
        raise PipxError(
            f"Application {app!r} is missing from environment {package!r} at {app_path}.\n"
            f"Reinstall it with `pipx reinstall {package}`.",
            wrap_message=False,
        )

    environment: Final[dict[str, str]] = dict(os.environ)
    environment["VIRTUAL_ENV"] = str(venv_dir)
    environment["PATH"] = (
        os.pathsep.join((str(venv.bin_path), path)) if (path := environment.get("PATH")) else str(venv.bin_path)
    )
    exec_app([app_path, *app_args], env=environment)


def _application_paths(venv: Venv) -> dict[str, Path]:
    packages: Final[tuple[PackageInfo, ...]] = (
        venv.pipx_metadata.main_package,
        *venv.pipx_metadata.injected_packages.values(),
    )
    return {
        _logical_app_name(path): path
        for package in packages
        for path in chain(package.app_paths, *package.app_paths_of_dependencies.values())
    }


def _logical_app_name(path: Path) -> str:
    return path.stem if WINDOWS and path.suffix.lower() == ".exe" else path.name


__all__ = [
    "execute",
]
