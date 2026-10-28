Under the uv backend, ``--index-url`` (``-i``) now reaches uv as ``--default-index``. uv let ``UV_DEFAULT_INDEX`` or a
default ``[[index]]`` entry override a command-line ``--index-url``, so ``pipx run``, ``install``, ``upgrade`` and
``outdated`` used the default index instead of the one named on the command line.
