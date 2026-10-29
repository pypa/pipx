Stop recording pip options that name a one-shot input or an output location, such as ``-r requirements.txt``,
``--group``, ``--log``, ``--report``, ``--cache-dir`` or ``--target``, and uv's ``--directory`` and ``--project``: they
apply to the command they were given on, and a later ``pipx upgrade`` or ``pipx reinstall`` no longer reads or writes
those paths again. pipx reads pip arguments as pip does, so a clustered short option such as ``-qr requirements.txt``
or an abbreviation such as ``--log-f pip.log`` counts too, and ``pipx runpip`` now finds an editable install written
as ``-qe ./project`` or ``-e./project`` the same way. On POSIX, ``pipx upgrade``, ``pipx reinstall`` and the other
commands that replay recorded arguments stop with an error, before the installer runs and without changing the record,
when a recorded ``--find-links``, ``--constraint``, ``--build-constraint``, ``--cert``, ``--client-cert``, uv's
``--config-file``, ``--overrides`` or ``--excludes``, or a ``file://`` or local-path index URL points at a path another
account could change. Pass the options again with ``--pip-args`` to use them for that run. ``pipx list --outdated``
reports such an environment as failed instead of checking it against that path.
