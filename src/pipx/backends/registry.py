from __future__ import annotations

__lazy_modules__ = ["pipx.backends._base", "pipx.backends.pip", "pipx.backends.uv", "pipx.util"]

import os
from functools import cache

from pipx.backends._base import KNOWN_BACKENDS, PIP, UV, Backend
from pipx.backends.pip import PipBackend
from pipx.backends.uv import UvBackend, find_uv_binary, uv_meets_minimum_version
from pipx.util import PipxError


def resolve_backend_name(
    *,
    cli_value: str | None = None,
    env_value: str | None,
    metadata_value: str | None = None,
    auto: bool = True,
) -> tuple[str, str]:
    # metadata outranks env so PIPX_DEFAULT_BACKEND=uv cannot retarget pip-backed venvs already on disk
    for candidate, source in ((cli_value, "cli"), (metadata_value, "metadata"), (env_value, "env")):
        if (validated := _validate(candidate)) is not None:
            return validated, source
    if auto and (found := find_uv_binary())[0] is not None and uv_meets_minimum_version(found[0]):
        return UV, f"auto-{found[1]}"
    return PIP, "auto-pip"


def _validate(candidate: str | None) -> str | None:
    if not candidate:
        return None
    if candidate not in KNOWN_BACKENDS:
        msg = f"Unknown backend {candidate!r}. Valid backends: {', '.join(KNOWN_BACKENDS)}."
        raise PipxError(msg)
    return candidate


# cached so UvBackend.__init__ probes the version and logs once per process, though validation and construction both
# ask for the backend
@cache
def get_backend(name: str) -> Backend:
    if name == PIP:
        return PipBackend()
    if name == UV:
        return UvBackend()
    msg = f"Unknown backend {name!r}. Valid backends: {', '.join(KNOWN_BACKENDS)}."
    raise PipxError(msg)


def assert_not_pip_under_uv(package_name: str, backend_name: str) -> None:
    if package_name == "pip" and backend_name != PIP:
        msg = (
            "The 'pip' package cannot be installed or exposed via the uv backend, since uv venvs "
            "don't ship pip and the resulting environment would be inconsistent.\n"
            "Use `--backend pip` (or set PIPX_DEFAULT_BACKEND=pip) to install 'pip' as a tool."
        )
        raise PipxError(msg)


def env_default_backend() -> str | None:
    return raw.strip() if (raw := os.environ.get("PIPX_DEFAULT_BACKEND")) else None


__all__ = [
    "assert_not_pip_under_uv",
    "env_default_backend",
    "get_backend",
    "resolve_backend_name",
]
