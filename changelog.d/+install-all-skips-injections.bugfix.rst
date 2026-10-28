Leave an existing environment alone in ``pipx install-all`` without ``--force``. pipx said it was not modifying the
environment, then injected the snapshot's ``injected_packages`` into it anyway. Pass ``--force`` to bring existing
environments in line with the snapshot.
