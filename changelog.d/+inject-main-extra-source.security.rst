``pipx inject ENV 'APP[extra]'`` now adds the extra to the main package's recorded source instead of replacing it with
the bare name ``APP[extra]``. An app installed from a wheel, a directory or a URL no longer turns into the index's
project of the same name on the next ``pipx upgrade`` or ``pipx reinstall``. Extras accumulate with the ones already
recorded, and a main-package spec that changes the version, path or URL needs ``--force``.
