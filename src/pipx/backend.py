import logging
import os
import shutil

DEFAULT_BACKEND = os.getenv("PIPX_DEFAULT_BACKEND", "venv")
DEFAULT_INSTALLER = os.getenv("PIPX_DEFAULT_INSTALLER", "pip")
SUPPORTED_VENV_BACKENDS = ("uv", "venv", "virtualenv")
SUPPORTED_INSTALLERS = ("uv", "pip")

logger = logging.getLogger(__name__)


def path_to_exec(executable: str, is_installer: bool = False) -> str:
    if executable in ("venv", "pip"):
        return executable
    path = shutil.which(executable)
    if path:
        return path
    elif is_installer:
        logger.warning(f"'{executable}' not found on PATH. Falling back to 'pip'.")
        return ""
    else:
        logger.warning(f"'{executable}' not found on PATH. Falling back to 'venv'.")
        return ""
