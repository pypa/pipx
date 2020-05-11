import os
import sys
from pathlib import Path
from textwrap import dedent

DEFAULT_PYTHON = sys.executable
DEFAULT_PIPX_HOME = Path.home() / ".local/pipx"
DEFAULT_PIPX_BIN_DIR = Path.home() / ".local/bin"
PIPX_HOME = Path(os.environ.get("PIPX_HOME", DEFAULT_PIPX_HOME)).resolve()
PIPX_LOCAL_VENVS = PIPX_HOME / "venvs"
DEFAULT_PIPX_SHARED_LIBS = PIPX_HOME / "shared"
PIPX_SHARED_LIBS = Path(
    os.environ.get("PIPX_SHARED_LIBS", DEFAULT_PIPX_SHARED_LIBS)
).resolve()
PIPX_SHARED_PTH = "pipx_shared.pth"
LOCAL_BIN_DIR = Path(os.environ.get("PIPX_BIN_DIR", DEFAULT_PIPX_BIN_DIR)).resolve()
PIPX_VENV_CACHEDIR = PIPX_HOME / ".cache"
TEMP_VENV_EXPIRATION_THRESHOLD_DAYS = 14


def is_windows() -> bool:
    try:
        WindowsError  # noqa
    except NameError:
        return False
    else:
        return True


WINDOWS: bool = is_windows()


def strtobool(val: str) -> bool:
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        return False


def use_emjois():
    platform_emoji_support = not is_windows() and sys.getdefaultencoding() == "utf-8"
    return strtobool(str(os.getenv("USE_EMOJI", platform_emoji_support)))


emoji_support = use_emjois()

completion_instructions = dedent(
    """
Add the appropriate command to your shell's config file
so that it is run on startup. You will likely have to restart
or re-login for the autocompletion to start working.

bash:
    eval "$(register-python-argcomplete pipx)"

zsh:
    To activate completions for zsh you need to have
    bashcompinit enabled in zsh:

    autoload -U bashcompinit
    bashcompinit

    Afterwards you can enable completion for pipx:

    eval "$(register-python-argcomplete pipx)"

tcsh:
    eval `register-python-argcomplete --shell tcsh pipx`

fish:
    register-python-argcomplete --shell fish pipx | .

"""
)
