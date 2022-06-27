import os
import sys


def strtobool(val: str) -> bool:
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        return False


def use_emojis() -> bool:
    # All emojis that pipx might possibly use
    emoji_test_str = "✨🌟⚠️😴⣷⣯⣟⡿⢿⣻⣽⣾"
    try:
        emoji_test_str.encode(sys.stderr.encoding)
        platform_emoji_support = True
    except UnicodeEncodeError:
        platform_emoji_support = False
    return strtobool(str(os.getenv("USE_EMOJI", platform_emoji_support)))


EMOJI_SUPPORT = use_emojis()


class Emoji:
    """
    A class to make monkey patching EMOJI_SUPPORT from tests work.

    The capfd fixture causes problems on Windows when the original stdout
    encoding cannot handle emoji.
    """

    def __init__(self, emoji):
        self.emoji = emoji

    def __str__(self) -> str:
        if EMOJI_SUPPORT:
            return self.emoji

        return ""


stars = Emoji("✨ 🌟 ✨")
hazard = Emoji("⚠️")
error = Emoji("⛔")
sleep = Emoji("😴")
