import sys
from constants import MINIMUM_PYTHON_VERSION

if sys.version_info < tuple(int(number) for number in MINIMUM_PYTHON_VERSION.split(".")):
    sys.exit(
       f"Python {MINIMUM_PYTHON_VERSION} or later is required. "
        "See https://github.com/pypa/pipx "
        "for installation instructions."
    )
