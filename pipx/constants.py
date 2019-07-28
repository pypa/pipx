import os
import sys
from pathlib import Path
from textwrap import dedent

DEFAULT_PYTHON = sys.executable
DEFAULT_PIPX_HOME = Path.home() / ".local/pipx"
DEFAULT_PIPX_BIN_DIR = Path.home() / ".local/bin"
PIPX_HOME = Path(os.environ.get("PIPX_HOME", DEFAULT_PIPX_HOME)).resolve()
PIPX_LOCAL_VENVS = PIPX_HOME / "venvs"
LOCAL_BIN_DIR = Path(os.environ.get("PIPX_BIN_DIR", DEFAULT_PIPX_BIN_DIR)).resolve()
PIPX_VENV_CACHEDIR = PIPX_HOME / ".cache"
PIPX_PACKAGE_NAME = "pipx"
TEMP_VENV_EXPIRATION_THRESHOLD_DAYS = 14

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
