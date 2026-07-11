import os
import sys


def strtobool(val: str) -> bool:
    return val.lower() in ("y", "yes", "t", "true", "on", "1")


def use_emojis() -> bool:
    if (use_emoji := os.getenv("PIPX_USE_EMOJI")) is not None:
        return strtobool(use_emoji)
    if (use_emoji := os.getenv("USE_EMOJI")) is not None:
        return strtobool(use_emoji)
    if (encoding := getattr(sys.stderr, "encoding", None)) is None:
        return False
    try:
        "✨🌟⚠️😴⣷⣯⣟⡿⢿⣻⣽⣾".encode(encoding)
    except UnicodeEncodeError:
        return False
    return True


EMOJI_SUPPORT = use_emojis()

if EMOJI_SUPPORT:
    stars = "✨ 🌟 ✨"
    hazard = "⚠️"
    error = "⛔"
    sleep = "😴"
else:
    stars = ""
    hazard = ""
    error = ""
    sleep = ""


__all__ = [
    "EMOJI_SUPPORT",
    "error",
    "hazard",
    "sleep",
    "stars",
    "strtobool",
    "use_emojis",
]
