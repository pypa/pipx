from __future__ import annotations

import os
from functools import cache

from pipx.backends._base import KNOWN_BACKENDS, PIP, UV, Backend
from pipx.backends.pip import PipBackend
from pipx.backends.uv import UvBackend, find_uv_binary
from pipx.util import PipxError


def resolve_backend_name(
    *,
    cli_value: str | None = None,
    env_value: str | None = None,
    metadata_value: str | None = None,
    auto: bool = True,
) -> tuple[str, str]:
    """Return ``(name, source)`` per precedence cli > metadata > env > auto.

    ``metadata`` sits above ``env`` so ``PIPX_DEFAULT_BACKEND=uv`` cannot
    silently retarget pip-backed venvs already on disk.
    """
    for candidate, source in ((cli_value, "cli"), (metadata_value, "metadata"), (env_value, "env")):
        if (validated := _validate(candidate)) is not None:
            return validated, source
    if auto and (binary_source := find_uv_binary()[1]) != "missing":
        return UV, f"auto-{binary_source}"
    return PIP, "auto-pip"


@cache
def get_backend(name: str) -> Backend:
    # Cached so ``UvBackend.__init__``'s version probe and log line fire once
    # per process even when validation + construction both ask for the backend.
    if name == PIP:
        return PipBackend()
    if name == UV:
        return UvBackend()
    raise PipxError(f"Unknown backend {name!r}. Valid backends: {', '.join(KNOWN_BACKENDS)}.")


def assert_not_pip_under_uv(package_name: str, backend_name: str) -> None:
    # Named narrowly: a future backend with its own deny-list should grow its
    # own guard rather than overload this one.
    if package_name == "pip" and backend_name != PIP:
        raise PipxError(
            "The 'pip' package cannot be installed or exposed via the uv backend, since uv venvs "
            "don't ship pip and the resulting environment would be inconsistent.\n"
            "Use `--backend pip` (or set PIPX_DEFAULT_BACKEND=pip) to install 'pip' as a tool."
        )


def env_default_backend() -> str | None:
    raw = os.environ.get("PIPX_DEFAULT_BACKEND")
    return raw.strip() if raw else None


def _validate(candidate: str | None) -> str | None:
    if not candidate:
        return None
    if candidate not in KNOWN_BACKENDS:
        raise PipxError(f"Unknown backend {candidate!r}. Valid backends: {', '.join(KNOWN_BACKENDS)}.")
    return candidate


__all__ = [
    "KNOWN_BACKENDS",
    "PIP",
    "UV",
    "Backend",
    "assert_not_pip_under_uv",
    "env_default_backend",
    "find_uv_binary",
    "get_backend",
    "resolve_backend_name",
]
