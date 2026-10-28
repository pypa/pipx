Keep the rollback backup of a running ``pipx reinstall``, ``reinstall-all``, ``install --force``, ``upgrade`` or
``inject`` when another pipx command starts. Every command used to empty the trash at startup, so a ``pipx list`` run
meanwhile deleted the backup, and when the first command then failed or was interrupted it lost the environment with a
``FileNotFoundError``. pipx now skips a backup while its environment's lock is held and removes it only once orphaned.
