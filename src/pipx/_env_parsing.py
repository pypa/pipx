from __future__ import annotations

__lazy_modules__ = ["typing"]

from typing import Final

from pipx.constants import FetchPythonOptions


def compute_fetch_python(missing_raw: str | None, python_raw: str | None) -> tuple[FetchPythonOptions, bool]:
    fetch_missing: Final[bool] = (missing_raw or "").strip().lower() not in {"", "0", "false", "f", "no", "n", "off"}
    raw: Final[str] = python_raw or (
        FetchPythonOptions.MISSING.value if fetch_missing else FetchPythonOptions.NEVER.value
    )
    try:
        return FetchPythonOptions(raw), False
    except ValueError:
        return FetchPythonOptions.NEVER, True


def compute_cooldown(raw: str | None) -> tuple[int | None, bool]:
    if raw is None or not (stripped := raw.strip()):
        return None, False
    try:
        days: Final[int] = int(stripped)
    except ValueError:
        return None, True
    return (days, False) if days >= 0 else (None, True)


def compute_max_logs(raw: str | None) -> tuple[int, bool]:
    if raw is None or not (stripped := raw.strip()):
        return 10, False
    try:
        logs: Final[int] = int(stripped)
    except ValueError:
        return 10, True
    return (logs, False) if logs >= 0 else (10, True)


__all__ = [
    "compute_cooldown",
    "compute_fetch_python",
    "compute_max_logs",
]
