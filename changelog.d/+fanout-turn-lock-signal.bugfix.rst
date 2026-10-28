A second Ctrl-C during ``pipx reinstall-all``, ``upgrade-all`` or ``install-all`` no longer hangs pipx. A signal
handled just after a worker took the shared lock could leave it held, so every other task waited forever.
