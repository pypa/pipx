Remove unreachable ``path.unlink()`` call in ``_remove_stale_reinstall_resources``;
``safe_unlink`` already removes both regular files and symlinks, so the subsequent
``is_symlink()`` check always returned ``False``.
