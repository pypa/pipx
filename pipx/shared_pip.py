import sys
from pathlib import Path

# Venv is a circular import...
from . import Venv
from .constants import PIPX_SHARED_PIP
from typing import List
from pipx.util import WINDOWS

_pip_venv = None


def get_shared_pip() -> Path:
    global _pip_venv
    if _pip_venv is None:
        _pip_venv = PIPX_SHARED_PIP
        if not _pip_venv.exists():
            Venv._run([sys.executable, "-m", "venv", _pip_venv])
            Venv._run(
                [
                    _pip_venv / "Scripts/python.exe",
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    "pip",
                    "setuptools",
                    "wheel",
                    "--disable-pip-version-check",
                ]
            )
    if WINDOWS:
        site_packages = "Lib/site-packages"
    else:
        site_packages = "lib/python{}.{}/site-packages".format(*sys.version_info[:2])

    return _pip_venv / site_packages
