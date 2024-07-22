from pipx.constants import DEFAULT_BACKEND

import logging
import shutil
from typing import Optional

SUPPORTED_BACKEND = ("uv", "venv", "virtualenv")
SUPPORTED_INSTALLER = ("uv", "pip")

logger = logging.getLogger(__name__)


def path_to_exec(executable: str, installer: bool = False) -> str:
    path = shutil.which(executable)
    if path:
        return path
    elif installer:
        logger.warning(f"{executable} not found on PATH. Falling back to pip.")
        return "pip"
    else:
        logger.warning(f"{executable} not found on PATH. Falling back to venv.")
        return "venv"
