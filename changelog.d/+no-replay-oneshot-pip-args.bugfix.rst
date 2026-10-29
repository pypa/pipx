Stop recording pip options that name a one-shot input or an output location, such as ``-r requirements.txt``,
``--log``, ``--report``, ``--cache-dir`` or ``--target``: they apply to the command they were given on, and a later
``pipx upgrade`` or ``pipx reinstall`` no longer reads or writes those paths again. On POSIX, a recorded
``--find-links``, ``--constraint``, ``--build-constraint``, ``--cert`` or ``--client-cert`` path that another account
could change is dropped with a warning instead of replayed.
