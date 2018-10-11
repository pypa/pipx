#/usr/bin/bash

set -e

pipx --help
pipx --version
pipx uninstall-all
pipx list
pipx pyxtermjs --help
pipx --version
pipx --spec git+https://github.com/ambv/black.git black --help
pipx --spec git+https://github.com/ambv/black.git#egg=black black --help
pipx https://gist.githubusercontent.com/cs01/fa721a17a326e551ede048c5088f9e0f/raw/6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py
pipx pipx --version