import sys
from pathlib import Path

# Venv is a circular import...
from . import Venv
from .constants import PIPX_SHARED_PIP
from pipx.util import WINDOWS

_pip_venv = None


def get_shared_pip() -> Path:
    global _pip_venv
    if _pip_venv is None:
        _pip_venv = PIPX_SHARED_PIP
        if not _pip_venv.exists():
            bin_path = _pip_venv / ("bin" if not WINDOWS else "Scripts")
            python_path = bin_path / ("python" if not WINDOWS else "python.exe")

            Venv._run([sys.executable, "-m", "venv", _pip_venv])
            Venv._run(
                [
                    python_path,
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
    site_packages = _pip_venv / ("lib" if not WINDOWS else "Lib")
    if not WINDOWS:
        site_packages = site_packages / "python{}.{}".format(*sys.version_info[:2])
    site_packages = site_packages / "site-packages"

    return site_packages
