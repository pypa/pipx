import sys
from pathlib import Path

# Venv is a circular import...
from . import Venv
from .constants import PIPX_SHARED_PIP
from typing import List

_pip_venv = None

def get_shared_pip() -> Path:
    global _pip_venv
    if _pip_venv is None:
        _pip_venv = PIPX_SHARED_PIP
        if not _pip_venv.exists():
            Venv._run([sys.executable, "-m", "venv", _pip_venv])
    return _pip_venv / "lib/site-packages"
