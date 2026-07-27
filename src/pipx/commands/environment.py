from __future__ import annotations

import os
from functools import cache
from typing import TYPE_CHECKING, Final

from pipx import paths
from pipx.backends import env_default_backend, find_uv_binary, resolve_backend_name
from pipx.constants import EXIT_CODE_OK, ExitCode
from pipx.emojis import EMOJI_SUPPORT
from pipx.interpreter import get_default_python
from pipx.shared_libs import (
    DISABLE_SHARED_LIBS_AUTO_UPGRADE,
    shared_libs_auto_upgrade_disabled,
)
from pipx.util import PipxError

if TYPE_CHECKING:
    from collections.abc import Callable

ENVIRONMENT_VARIABLES: Final = [
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
    "PIPX_FETCH_MISSING_PYTHON",
    "PIPX_FETCH_PYTHON",
    DISABLE_SHARED_LIBS_AUTO_UPGRADE,
    "PIPX_USE_EMOJI",
]
DERIVED_ENVIRONMENT_VARIABLES: Final = [
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
ENVIRONMENT_VALUE_CHOICES: Final = ENVIRONMENT_VARIABLES + DERIVED_ENVIRONMENT_VARIABLES


def _get_derived_values() -> dict[str, Callable[[], object]]:
    @cache
    def resolve_backend() -> tuple[str, str]:
        return resolve_backend_name(env_value=env_default_backend())

    return {
        "PIPX_HOME": lambda: paths.ctx.home,
        "PIPX_BIN_DIR": lambda: paths.ctx.bin_dir,
        "PIPX_MAN_DIR": lambda: paths.ctx.man_dir,
        "PIPX_COMPLETION_DIR": lambda: paths.ctx.completion_dir,
        "PIPX_SHARED_LIBS": lambda: paths.ctx.shared_libs,
        "PIPX_LOCAL_VENVS": lambda: paths.ctx.venvs,
        "PIPX_LOG_DIR": lambda: paths.ctx.logs,
        "PIPX_TRASH_DIR": lambda: paths.ctx.trash,
        "PIPX_VENV_CACHEDIR": lambda: paths.ctx.venv_cache,
        "PIPX_STANDALONE_PYTHON_CACHEDIR": lambda: paths.ctx.standalone_python_cachedir,
        "PIPX_DEFAULT_PYTHON": get_default_python,
        "PIPX_RESOLVED_BACKEND": lambda: resolve_backend()[0],
        "PIPX_BACKEND_SOURCE": lambda: resolve_backend()[1],
        "PIPX_UV_BINARY": lambda: str(binary) if (binary := find_uv_binary()[0]) else "",
        "UV_CACHE_DIR": lambda: os.environ.get("UV_CACHE_DIR", ""),
        DISABLE_SHARED_LIBS_AUTO_UPGRADE: lambda: str(shared_libs_auto_upgrade_disabled()).lower(),
        "PIPX_USE_EMOJI": lambda: str(EMOJI_SUPPORT).lower(),
    }


def environment(value: str | None) -> ExitCode:
    """Print a list of environment variables and paths used by pipx"""
    derived_values = _get_derived_values()
    if value is None:
        print("Environment variables (set by user):")  # ruff:ignore[print]  # user-facing CLI output
        print()  # ruff:ignore[print]
        for env_variable in ENVIRONMENT_VARIABLES:
            print(f"{env_variable}={os.getenv(env_variable, '')}")  # ruff:ignore[print]
        print()  # ruff:ignore[print]
        print("Derived values (computed by pipx):")  # ruff:ignore[print]
        print()  # ruff:ignore[print]
        for env_variable, resolve_derived_value in derived_values.items():
            print(f"{env_variable}={resolve_derived_value()}")  # ruff:ignore[print]
    elif (get_derived_value := derived_values.get(value)) is not None:
        print(get_derived_value())  # ruff:ignore[print]
    elif value in ENVIRONMENT_VARIABLES:
        print(os.getenv(value, ""))  # ruff:ignore[print]
    else:
        msg = "Variable not found."
        raise PipxError(msg)

    return EXIT_CODE_OK


__all__ = [
    "ENVIRONMENT_VALUE_CHOICES",
    "ENVIRONMENT_VARIABLES",
    "environment",
]
