from __future__ import annotations

__lazy_modules__ = ["typing"]

import os
import sys
from typing import Final


def strtobool(value: str) -> bool:
    return value.lower() in {"y", "yes", "t", "true", "on", "1"}


def use_emojis() -> bool:
    for variable in ("PIPX_USE_EMOJI", "USE_EMOJI"):
        if (use_emoji := os.getenv(variable)) is not None:
            return strtobool(use_emoji)
    if (encoding := getattr(sys.stderr, "encoding", None)) is None:
        return False
    try:
        "✨🌟⚠️😴⣷⣯⣟⡿⢿⣻⣽⣾".encode(encoding)
    except UnicodeEncodeError:
        return False
    return True


EMOJI_SUPPORT: Final[bool] = use_emojis()

STARS: Final[str] = "✨ 🌟 ✨" if EMOJI_SUPPORT else ""
HAZARD: Final[str] = "⚠️" if EMOJI_SUPPORT else ""
ERROR: Final[str] = "⛔" if EMOJI_SUPPORT else ""
SLEEP: Final[str] = "😴" if EMOJI_SUPPORT else ""


__all__ = [
    "EMOJI_SUPPORT",
    "ERROR",
    "HAZARD",
    "SLEEP",
    "STARS",
    "strtobool",
    "use_emojis",
]
