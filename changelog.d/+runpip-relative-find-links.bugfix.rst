``pipx runpip <venv> install`` now records a relative ``--find-links`` (``-f``) path as an absolute path under the
directory you ran it from. A later ``pipx upgrade`` or ``pipx reinstall`` read it against the environment's directory
instead, failed with ``Failed to read --find-links directory`` or found no matching distribution, and rolled back.
