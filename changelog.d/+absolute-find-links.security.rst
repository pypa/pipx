Record relative ``--find-links`` and ``--constraint`` values passed to ``pipx upgrade --pip-args`` and ``pipx run``
scripts as absolute paths, resolve relative values already in ``pipx_metadata.json`` against the environment's
directory, and run the shared pip refresh inside the shared libraries directory, so a later ``pipx upgrade`` or ``pipx
reinstall`` no longer reads wheels from whatever directory you start it in.
