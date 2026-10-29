Stop a self-managed pipx (``pipx install pipx``) started through its own environment's script from taking that
environment's ``bin`` directory for ``PIPX_BIN_DIR`` when the path to the script holds ``..`` or a symlinked directory,
such as ``../share/pipx/venvs/pipx/bin/pipx`` from ``~/.local/bin``. Such a command linked the apps it installed into
pipx's own environment, off ``PATH`` and onto pipx's own import path. pipx now recognizes the exposed link by real
locations, which also works when you reach the pipx home through a symlink.
