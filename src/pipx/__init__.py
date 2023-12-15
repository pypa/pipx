import sys

if sys.version_info < (3, 8, 0):
    sys.exit("Python 3.8 or later is required. " "See https://github.com/pypa/pipx " "for installation instructions.")
