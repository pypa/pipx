Ignore apps, man pages and completions whose name is not a plain file name, such as ``..``, and never delete a
directory to make room for an app link, so ``pipx reinstall`` can no longer remove the parent of ``PIPX_BIN_DIR``.
