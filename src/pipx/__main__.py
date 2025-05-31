import os
import sys

if not __package__:
    # Running from source. Add pipx's source code to the system
    # path to allow direct invocation, such as:
    #   python src/pipx --help
    pipx_package_source_path = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(0, pipx_package_source_path)

from pipx.main import cli

if __name__ == "__main__":
    sys.exit(cli())
