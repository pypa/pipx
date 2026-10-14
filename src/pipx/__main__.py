# PYTHON_ARGCOMPLETE_OK

from __future__ import annotations

__lazy_modules__ = ["typing"]

import pathlib
import sys
from typing import Final

if sys.version_info >= (3, 15):
    # defers every module-level import in the process, third-party ones included; these modules snapshot terminal state
    # and environment variables at import (and run colorama.init() on Windows), so they keep loading at startup
    _EAGER_MODULES: Final[frozenset[str]] = frozenset({"pipx.animate", "pipx.colors", "pipx.constants", "pipx.emojis"})
    sys.set_lazy_imports_filter(
        lambda _importer, name, fromlist: (
            name not in _EAGER_MODULES and _EAGER_MODULES.isdisjoint(f"{name}.{item}" for item in fromlist or ())
        )
    )
    sys.set_lazy_imports("all")

if not __spec__ or not __spec__.parent:
    # Running from source. Add pipx's source code to the system
    # path to allow direct invocation, such as:
    #   python src/pipx --help
    pipx_package_source_path = pathlib.Path(pathlib.Path(__file__).parent).parent
    sys.path.insert(0, str(pipx_package_source_path))

from pipx.main import cli

if __name__ == "__main__":
    sys.exit(cli())
