from __future__ import annotations

__lazy_modules__ = ["functools", "pipx", "pipx.backends.registry", "pipx.backends.uv", "pipx.interpreter", "pipx.util"]

import os
from functools import cache
from typing import TYPE_CHECKING, Final

from pipx import paths
from pipx.backends.registry import env_default_backend, resolve_backend_name
from pipx.backends.uv import find_uv_binary
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
    from pathlib import Path

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
ENVIRONMENT_VALUE_CHOICES: Final[list[str]] = ENVIRONMENT_VARIABLES + DERIVED_ENVIRONMENT_VARIABLES


def environment(value: str | None) -> ExitCode:
    derived_values: Final[dict[str, Callable[[], Path | str]]] = _get_derived_values()
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


def _get_derived_values() -> dict[str, Callable[[], Path | str]]:
    @cache
    def resolve_backend() -> tuple[str, str]:
        return resolve_backend_name(env_value=env_default_backend())

    return {
        "PIPX_HOME": lambda: paths.CTX.home,
        "PIPX_BIN_DIR": lambda: paths.CTX.bin_dir,
        "PIPX_MAN_DIR": lambda: paths.CTX.man_dir,
        "PIPX_COMPLETION_DIR": lambda: paths.CTX.completion_dir,
        "PIPX_SHARED_LIBS": lambda: paths.CTX.shared_libs,
        "PIPX_LOCAL_VENVS": lambda: paths.CTX.venvs,
        "PIPX_LOG_DIR": lambda: paths.CTX.logs,
        "PIPX_TRASH_DIR": lambda: paths.CTX.trash,
        "PIPX_VENV_CACHEDIR": lambda: paths.CTX.venv_cache,
        "PIPX_STANDALONE_PYTHON_CACHEDIR": lambda: paths.CTX.standalone_python_cachedir,
        "PIPX_DEFAULT_PYTHON": get_default_python,
        "PIPX_RESOLVED_BACKEND": lambda: resolve_backend()[0],
        "PIPX_BACKEND_SOURCE": lambda: resolve_backend()[1],
        "PIPX_UV_BINARY": lambda: str(binary) if (binary := find_uv_binary()[0]) else "",
        "UV_CACHE_DIR": lambda: os.environ.get("UV_CACHE_DIR", ""),
        DISABLE_SHARED_LIBS_AUTO_UPGRADE: lambda: str(shared_libs_auto_upgrade_disabled()).lower(),
        "PIPX_USE_EMOJI": lambda: str(EMOJI_SUPPORT).lower(),
    }


__all__ = [
    "DERIVED_ENVIRONMENT_VARIABLES",
    "ENVIRONMENT_VALUE_CHOICES",
    "ENVIRONMENT_VARIABLES",
    "environment",
]
