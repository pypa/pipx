from __future__ import annotations

__lazy_modules__ = ["typing"]

import os
import sys
from typing import Final


def strtobool(value: str) -> bool:
    """Return whether a text reads as a true value, such as ``yes`` or ``1``.

    :param value: the text to read.
    :returns: whether the text is a true value.
    """
    return value.lower() in {"y", "yes", "t", "true", "on", "1"}


def use_emojis() -> bool:
    """Return whether the output can show emojis.

    The variables ``PIPX_USE_EMOJI`` and ``USE_EMOJI`` override the detection, the first one set wins.

    :returns: whether emojis are shown.
    """
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


#: Whether emojis are shown in the output.
EMOJI_SUPPORT: Final[bool] = use_emojis()

#: Star marks for the end of a successful command, or an empty string when emojis are off.
STARS: Final[str] = "✨ 🌟 ✨" if EMOJI_SUPPORT else ""
#: Warning marker for a hazard, or an empty string when emojis are off.
HAZARD: Final[str] = "⚠️" if EMOJI_SUPPORT else ""
#: Error marker, or an empty string when emojis are off.
ERROR: Final[str] = "⛔" if EMOJI_SUPPORT else ""
#: Marker for a sleeping command, or an empty string when emojis are off.
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
