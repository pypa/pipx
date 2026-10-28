Stop a self-managed pipx (``pipx install pipx``) started through its own environment's script from taking that
environment's ``bin`` directory for ``PIPX_BIN_DIR`` when the path to the script holds ``..`` or a symlinked directory,
such as ``../share/pipx/venvs/pipx/bin/pipx`` from ``~/.local/bin``. Apps installed by such a command were linked into
pipx's own environment, off ``PATH`` and onto pipx's own import path. The exposed link is now recognized by real
locations, which also makes it work when the pipx home is reached through a symlink.
