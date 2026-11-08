from __future__ import annotations

__lazy_modules__ = [
    "functools",
    "pipx.backends.registry",
    "pipx.backends.uv",
    "pipx.interpreter",
    "pipx.paths",
    "pipx.util",
]

import os
from functools import cache
from typing import TYPE_CHECKING, Final

from pipx.backends.registry import env_default_backend, resolve_backend_name
from pipx.backends.uv import find_uv_binary
from pipx.constants import EXIT_CODE_OK, ExitCode
from pipx.emojis import EMOJI_SUPPORT
from pipx.interpreter import get_default_python
from pipx.paths import CTX
from pipx.shared_libs import (
    DISABLE_SHARED_LIBS_AUTO_UPGRADE,
    shared_libs_auto_upgrade_disabled,
)
from pipx.util import PipxError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

#: Environment variables that users set to change pipx's behavior.
ENVIRONMENT_VARIABLES: Final[list[str]] = [
    "PIPX_HOME",
    "PIPX_GLOBAL_HOME",
    "PIPX_BIN_DIR",
    "PIPX_GLOBAL_BIN_DIR",
    "PIPX_MAN_DIR",
    "PIPX_COMPLETION_DIR",
    "PIPX_GLOBAL_MAN_DIR",
    "PIPX_GLOBAL_COMPLETION_DIR",
    "PIPX_SHARED_LIBS",
    "PIPX_DEFAULT_PYTHON",
    "PIPX_DEFAULT_BACKEND",
    "PIPX_COOLDOWN",
    "PIPX_FETCH_MISSING_PYTHON",
    "PIPX_FETCH_PYTHON",
    DISABLE_SHARED_LIBS_AUTO_UPGRADE,
    "PIPX_USE_EMOJI",
    "PIPX_MAX_LOGS",
]
#: Environment variables that pipx derives from the ones users set.
DERIVED_ENVIRONMENT_VARIABLES: Final[list[str]] = [
    "PIPX_LOCAL_VENVS",
    "PIPX_LOG_DIR",
    "PIPX_TRASH_DIR",
    "PIPX_VENV_CACHEDIR",
    "PIPX_STANDALONE_PYTHON_CACHEDIR",
    "PIPX_RESOLVED_BACKEND",
    "PIPX_BACKEND_SOURCE",
    "PIPX_UV_BINARY",
    "UV_CACHE_DIR",
]
#: Every environment variable that the environment command accepts.
ENVIRONMENT_VALUE_CHOICES: Final[list[str]] = ENVIRONMENT_VARIABLES + DERIVED_ENVIRONMENT_VARIABLES


def environment(value: str | None) -> ExitCode:
    """Print the environment variables pipx reads, or the value of one of them.

    :param value: the variable to print, all of them when None.
    :returns: the exit code.
    :raises PipxError: when the variable is not one pipx reads.
    """

    @cache
    def resolve_backend() -> tuple[str, str]:
        return resolve_backend_name(env_value=env_default_backend())

    derived_values: Final[dict[str, Callable[[], Path | str]]] = {
        "PIPX_HOME": lambda: CTX.home,
        "PIPX_BIN_DIR": lambda: CTX.bin_dir,
        "PIPX_MAN_DIR": lambda: CTX.man_dir,
        "PIPX_COMPLETION_DIR": lambda: CTX.completion_dir,
        "PIPX_SHARED_LIBS": lambda: CTX.shared_libs,
        "PIPX_LOCAL_VENVS": lambda: CTX.venvs,
        "PIPX_LOG_DIR": lambda: CTX.logs,
        "PIPX_TRASH_DIR": lambda: CTX.trash,
        "PIPX_VENV_CACHEDIR": lambda: CTX.venv_cache,
        "PIPX_STANDALONE_PYTHON_CACHEDIR": lambda: CTX.standalone_python_cachedir,
        "PIPX_DEFAULT_PYTHON": get_default_python,
        "PIPX_RESOLVED_BACKEND": lambda: resolve_backend()[0],
        "PIPX_BACKEND_SOURCE": lambda: resolve_backend()[1],
        "PIPX_UV_BINARY": lambda: str(binary) if (binary := find_uv_binary()[0]) else "",
        "UV_CACHE_DIR": lambda: os.environ.get("UV_CACHE_DIR", ""),
        DISABLE_SHARED_LIBS_AUTO_UPGRADE: lambda: str(shared_libs_auto_upgrade_disabled()).lower(),
        "PIPX_USE_EMOJI": lambda: str(EMOJI_SUPPORT).lower(),
    }
    if value is None:
        print("Environment variables (set by user):")  # ruff:ignore[print]  # user-facing CLI output
        print()  # ruff:ignore[print]  # user-facing CLI output
        for env_variable in ENVIRONMENT_VARIABLES:
            print(f"{env_variable}={os.getenv(env_variable, '')}")  # ruff:ignore[print]  # user-facing CLI output
        print()  # ruff:ignore[print]  # user-facing CLI output
        print("Derived values (computed by pipx):")  # ruff:ignore[print]  # user-facing CLI output
        print()  # ruff:ignore[print]  # user-facing CLI output
        for env_variable, resolve_derived_value in derived_values.items():
            print(f"{env_variable}={resolve_derived_value()}")  # ruff:ignore[print]  # user-facing CLI output
    elif (get_derived_value := derived_values.get(value)) is not None:
        print(get_derived_value())  # ruff:ignore[print]  # user-facing CLI output
    elif value in ENVIRONMENT_VARIABLES:
        print(os.getenv(value, ""))  # ruff:ignore[print]  # user-facing CLI output
    else:
        msg: Final[str] = "Variable not found."
        raise PipxError(msg)

    return EXIT_CODE_OK


__all__ = [
    "DERIVED_ENVIRONMENT_VARIABLES",
    "ENVIRONMENT_VALUE_CHOICES",
    "ENVIRONMENT_VARIABLES",
    "environment",
]
