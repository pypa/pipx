import sys

if sys.version_info < (3, 6, 0):
    sys.exit(
        "Python 3.6 or later is required. "
        "See https://github.com/pipxproject/pipx "
        "for installation instructions."
    )
