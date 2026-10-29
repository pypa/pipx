pipx now recognises the app copies it made when the environment's interpreter path is too long for a shebang line or
contains a space. pip and uv start such launchers with a ``#!/bin/sh`` line that hands over to the interpreter, and pipx
took ``/bin/sh`` for the interpreter, so ``pipx reinstall`` kept a stale copy and warned "File exists ... Not
modifying."
