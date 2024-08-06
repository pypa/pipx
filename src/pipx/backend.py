import logging
import shutil

SUPPORTED_VENV_BACKENDS = ("uv", "venv", "virtualenv")
SUPPORTED_INSTALLERS = ("uv", "pip")

logger = logging.getLogger(__name__)


def path_to_exec(executable: str, installer: bool = False) -> str:
    if executable in ("venv", "pip"):
        return executable
    path = shutil.which(executable)
    if path:
        return path
    elif installer:
        logger.warning(f"'{executable}' not found on PATH. Falling back to 'pip'.")
        return ""
    else:
        logger.warning(f"'{executable}' not found on PATH. Falling back to 'venv'.")
        return ""
