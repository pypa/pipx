import sys
from .version import __version__, __version_info__

__all__ = ["__version__", "__version_info__"]

if sys.version_info < (3, 6, 0):
    sys.exit(
        "Python 3.6 or later is required. "
        "See https://github.com/pipxproject/pipx "
        "for installation instructions."
    )
