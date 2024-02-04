import os

from pipx.constants import (
    EXIT_CODE_OK,
    LOCAL_BIN_DIR,
    LOCAL_MAN_DIR,
    PIPX_HOME,
    PIPX_LOCAL_VENVS,
    PIPX_LOG_DIR,
    PIPX_SHARED_LIBS,
    PIPX_STANDALONE_PYTHON_CACHEDIR,
    PIPX_TRASH_DIR,
    PIPX_VENV_CACHEDIR,
    ExitCode,
)
from pipx.emojis import EMOJI_SUPPORT
from pipx.interpreter import DEFAULT_PYTHON
from pipx.util import PipxError


def environment(value: str) -> ExitCode:
    """Print a list of environment variables and paths used by pipx"""
    environment_variables = [
        "PIPX_HOME",
        "PIPX_BIN_DIR",
        "PIPX_MAN_DIR",
        "PIPX_SHARED_LIBS",
        "PIPX_DEFAULT_PYTHON",
        "PIPX_FETCH_MISSING_PYTHON",
        "USE_EMOJI",
    ]
    derived_values = {
        "PIPX_HOME": PIPX_HOME,
        "PIPX_BIN_DIR": LOCAL_BIN_DIR,
        "PIPX_MAN_DIR": LOCAL_MAN_DIR,
        "PIPX_SHARED_LIBS": PIPX_SHARED_LIBS,
        "PIPX_LOCAL_VENVS": PIPX_LOCAL_VENVS,
        "PIPX_LOG_DIR": PIPX_LOG_DIR,
        "PIPX_TRASH_DIR": PIPX_TRASH_DIR,
        "PIPX_VENV_CACHEDIR": PIPX_VENV_CACHEDIR,
        "PIPX_STANDALONE_PYTHON_CACHEDIR": PIPX_STANDALONE_PYTHON_CACHEDIR,
        "PIPX_DEFAULT_PYTHON": DEFAULT_PYTHON,
        "USE_EMOJI": str(EMOJI_SUPPORT).lower(),
    }
    if value is None:
        print("Environment variables (set by user):")
        print("")
        for env_variable in environment_variables:
            env_value = os.getenv(env_variable, "")
            print(f"{env_variable}={env_value}")
        print("")
        print("Derived values (computed by pipx):")
        print("")
        for env_variable in derived_values:
            print(f"{env_variable}={derived_values[env_variable]}")
    elif value in derived_values:
        print(derived_values[value])
    else:
        raise PipxError("Variable not found.")

    return EXIT_CODE_OK
