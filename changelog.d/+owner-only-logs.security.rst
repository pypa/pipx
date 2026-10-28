pipx now creates its log directory readable by its owner only (``0700``), tightens an existing one, and writes
``cmd_*.log`` and ``cmd_*_{pip,uv}_errors.log`` as ``0600``. The logs record the full command line, including the
arguments ``pipx run`` and ``pipx exec`` pass to the application, and in a ``--global`` store under ``/opt/pipx/logs``
any local account could read them.
