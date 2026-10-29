On Windows under the uv backend, ``pipx upgrade pipx`` on a pipx that manages itself no longer fails with ``Access is
denied`` and rolls back. uv deletes the files it replaces, which Windows refuses for the running ``pipx.exe``, so pipx
now moves that launcher to its trash first, where the next pipx command deletes it.
