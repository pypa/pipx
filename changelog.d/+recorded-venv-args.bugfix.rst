Ignore recorded ``venv_args`` other than ``--system-site-packages``, with a warning, when reading a snapshot or
``pipx_metadata.json``, so ``pipx install-all`` and ``pipx reinstall`` no longer pass an edited ``--clear <dir>`` or an
extra directory to ``python -m venv``.
