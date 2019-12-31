import sys

if sys.version_info < (3, 6, 0):
    exit(
        "Python 3.6+ is required. See https://github.com/pipxproject/pipx "
        "for installation instructions."
    )
