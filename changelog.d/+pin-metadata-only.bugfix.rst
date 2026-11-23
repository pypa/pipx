``pipx pin`` and ``pipx unpin`` now update only the environment's metadata record, so both commands
succeed even when the environment's Python interpreter is broken or the original local package
source has been removed.
