import os

from pipx import paths
from pipx.constants import EXIT_CODE_OK, ExitCode
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
        "PIPX_HOME": paths.ctx.home,
        "PIPX_BIN_DIR": paths.ctx.bin_dir,
        "PIPX_MAN_DIR": paths.ctx.man_dir,
        "PIPX_SHARED_LIBS": paths.ctx.shared_libs,
        "PIPX_LOCAL_VENVS": paths.ctx.venvs,
        "PIPX_LOG_DIR": paths.ctx.logs,
        "PIPX_TRASH_DIR": paths.ctx.trash,
        "PIPX_VENV_CACHEDIR": paths.ctx.venv_cache,
        "PIPX_STANDALONE_PYTHON_CACHEDIR": paths.ctx.standalone_python_cachedir,
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
