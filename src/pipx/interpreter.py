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
        raise PipxError("no suitable Python found")

    # If the path contains "WindowsApps", it's the store python
    if "WindowsApps" not in python:
        return python

    # Special treatment to detect Windows Store stub.
    # https://twitter.com/zooba/status/1212454929379581952

    proc = subprocess.run(
        [python, "-V"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        # Cover the 9009 return code pre-emptively.
        raise PipxError("no suitable Python found")
    if not proc.stdout.strip():
        # A real Python should print version, Windows Store stub won't.
        raise PipxError("no suitable Python found")
    return python  # This executable seems to work.


if WINDOWS:
    DEFAULT_PYTHON = _find_default_windows_python()
else:
    DEFAULT_PYTHON = sys.executable
