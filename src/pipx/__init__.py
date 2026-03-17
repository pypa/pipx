import sys

if sys.version_info < (3, 9, 0):  # noqa: UP036
    sys.exit("Python 3.9 or later is required. See https://github.com/pypa/pipx for installation instructions.")
