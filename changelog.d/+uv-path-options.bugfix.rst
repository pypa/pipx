Extend the 1.18.8 handling of recorded pip arguments to uv's path options and to ``--group``. pipx no longer records
``--group``, or uv's ``--directory`` and ``--project``, which would move uv's configuration search away from
``PIPX_HOME``. On POSIX, a recorded ``--config-file``, ``--overrides``/``--override`` or ``--excludes``/``--exclude``
that points at a path another account could change stops ``pipx upgrade``, ``pipx reinstall`` and the other replaying
commands with the same error as ``--find-links``. ``pipx list --outdated`` runs the same check and reports such an
environment as failed instead of querying the recorded location. ``pipx runpip`` reads its install arguments with the
same parser, so it records an install written as ``-qe ./project`` or ``-e./project`` as editable.
