# Valid package specifiers for pipx:
#   git+<URL>
#   <URL>
#   <pypi_package_name>
#   <pypi_package_name><version_specifier>

from pathlib import Path
from pkg_resources import Requirement
import re
from typing import List
import urllib.parse

from pipx.util import valid_pypi_name
