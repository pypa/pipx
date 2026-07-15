from __future__ import annotations

import pathlib
import sys

if not __spec__ or not __spec__.parent:
    # Running from source. Add pipx's source code to the system
    # path to allow direct invocation, such as:
    #   python src/pipx --help
    pipx_package_source_path = pathlib.Path(pathlib.Path(__file__).parent).parent
    sys.path.insert(0, str(pipx_package_source_path))

from pipx.main import cli

if __name__ == "__main__":
    sys.exit(cli())
