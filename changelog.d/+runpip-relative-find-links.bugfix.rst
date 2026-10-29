``pipx runpip <venv> install`` now records a relative ``--find-links`` (``-f``) path resolved against the directory you
ran it from. Before, a later ``pipx upgrade`` or ``pipx reinstall`` read it against the environment's directory, failed
with ``Failed to read --find-links directory`` or ``No matching distribution found``, and rolled back.
