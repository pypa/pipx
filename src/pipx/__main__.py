# PYTHON_ARGCOMPLETE_OK

from __future__ import annotations

__lazy_modules__ = ["typing"]

import os
import sys

if not sys.flags.safe_path and __spec__ and __spec__.parent:
    # Python searches the directory of the script it started (the working directory under -m) ahead of the standard
    # library. pip writes the pipx script into the directory pipx links apps into, so an app named shlex.py would be
    # imported in place of that module; drop the entry before the next import, unless pipx itself was found through it
    # (cd src && python -m pipx).
    try:
        _SCRIPT_DIR: Final[str] = (
            os.getcwd()  # ruff:ignore[os-getcwd]  # no pathlib yet
            if __name__ == "__main__"
            else os.path.dirname(os.path.realpath(sys.argv[0]))  # ruff:ignore[os-path-dirname]  # no pathlib yet
        )
    except OSError:
        pass  # Python adds no entry for a working directory that is gone
    else:
        _PACKAGE_PARENT: Final[str] = os.path.dirname(os.path.dirname(__file__))  # ruff:ignore[os-path-dirname]  # no pathlib yet
        if sys.path[:1] == [_SCRIPT_DIR] != [_PACKAGE_PARENT]:
            del sys.path[0]

import pathlib
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
    # respect a mode the user picked; sys.flags.lazy_imports reads -1 for both unset and an explicit "normal"
    if not (
        "lazy_imports" in sys._xoptions  # ruff:ignore[private-member-access]  # documented home of -X options
        or (not sys.flags.ignore_environment and os.environ.get("PYTHON_LAZY_IMPORTS"))
    ):
        sys.set_lazy_imports("all")

if not __spec__ or not __spec__.parent:
    # python src/pipx runs this file outside its package, so put src on the path for the import below
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from pipx.main import cli

if __name__ == "__main__":
    sys.exit(cli())
