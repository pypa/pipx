Refuse a ``--python`` value that is not a version before ``--fetch-python=missing`` or ``--fetch-python=always`` looks
in the standalone interpreter cache. pipx joined the raw value onto ``PIPX_HOME/py`` and deleted the result as a failed
earlier download, so a directory path, ``..``, ``.`` or a bare ``python`` removed that directory, ``PIPX_HOME`` or the
whole interpreter cache.
