pipx no longer reads ``installed-files.txt`` from a distribution that has a ``RECORD``, matching ``importlib.metadata``.
A dependency, or a package injected without ``--include-apps``, could ship that file into the main package's
``.dist-info`` and get its own apps, man pages and completions exposed without ``--include-deps``.
