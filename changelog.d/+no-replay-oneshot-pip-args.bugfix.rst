Stop recording pip options that name a one-shot input or an output location, such as ``-r requirements.txt``,
``--log``, ``--report``, ``--cache-dir`` or ``--target``: they apply to the command they were given on, and a later
``pipx upgrade`` or ``pipx reinstall`` no longer reads or writes those paths. pipx reads pip arguments as pip does, so
a clustered short option such as ``-qr requirements.txt`` or an abbreviation such as ``--log-f pip.log`` counts too.
On POSIX, ``pipx upgrade``, ``pipx reinstall`` and the other commands that replay recorded arguments stop with an
error, before the installer runs and without changing the record, when a recorded ``--find-links``, ``--constraint``,
``--build-constraint``, ``--cert``, ``--client-cert``, or ``file://`` or local-path index URL points at a path another
account could change. Pass the options again with ``--pip-args`` to use them for that run.
