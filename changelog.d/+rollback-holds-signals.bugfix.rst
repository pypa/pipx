Finish restoring an environment when Ctrl-C, ``SIGTERM`` or ``SIGHUP`` arrives while a failed or interrupted ``pipx
reinstall``, ``install --force``, ``inject``, ``upgrade`` or ``manifest sync`` rolls it back. The rollback deletes the
half-built environment and then moves the backup in, and a signal between the two steps left the environment deleted
and its only copy in the trash, which the next pipx command emptied. pipx now holds such a signal until the backup is
back in place and acts on it afterwards.
