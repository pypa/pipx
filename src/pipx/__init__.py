import sys

if sys.version_info < (3, 10, 0):  # noqa: UP036
    sys.exit("Python 3.10 or later is required. See https://github.com/pypa/pipx for installation instructions.")
