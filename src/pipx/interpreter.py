import os
import shutil
import subprocess
import sys

from pipx.constants import WINDOWS
from pipx.util import PipxError


def has_venv() -> bool:
    try:
        import venv  # noqa

        return True
    except ImportError:
        return False


# The following code was copied from https://github.com/uranusjr/pipx-standalone
# which uses the same technique to build a completely standalone pipx
# distribution.
#
# If we are running under the Windows embeddable distribution,
# venv isn't available (and we probably don't want to use the
# embeddable distribution as our applications' base Python anyway)
# so we try to locate the system Python and use that instead.


def _find_default_windows_python() -> str:

    if has_venv():
        return sys.executable

    py = shutil.which("py")
    if py:
        return py
    python = shutil.which("python")
    if python is None:
        raise PipxError("No suitable Python found")

    # If the path contains "WindowsApps", it's the store python
    if "WindowsApps" not in python:
        return python

    # Special treatment to detect Windows Store stub.
    # https://twitter.com/zooba/status/1212454929379581952

    proc = subprocess.run(
        [python, "-V"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    if proc.returncode != 0:
        # Cover the 9009 return code pre-emptively.
        raise PipxError("No suitable Python found")
    if not proc.stdout.strip():
        # A real Python should print version, Windows Store stub won't.
        raise PipxError("No suitable Python found")
    return python  # This executable seems to work.


def _get_sys_executable() -> str:
    if WINDOWS:
        return _find_default_windows_python()
    else:
        return sys.executable


def _get_absolute_python_interpreter(env_python: str) -> str:
    which_python = shutil.which(env_python)
    if not which_python:
        raise PipxError(f"Default python interpreter {repr(env_python)} is invalid.")
    return which_python


env_default_python = os.environ.get("PIPX_DEFAULT_PYTHON")

if not env_default_python:
    DEFAULT_PYTHON = _get_sys_executable()
else:
    DEFAULT_PYTHON = _get_absolute_python_interpreter(env_default_python)
