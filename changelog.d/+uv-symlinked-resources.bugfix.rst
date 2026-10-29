With the uv backend and ``UV_LINK_MODE=symlink``, ``pipx uninstall`` now removes the man page and shell completion links
it exposed, and ``pipx list`` no longer reports those man pages as missing. uv makes the environment's own copies
symlinks into its cache, and pipx followed them there instead of stopping at the environment.
