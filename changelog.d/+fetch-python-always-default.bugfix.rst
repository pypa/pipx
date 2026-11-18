``--fetch-python=always`` (or ``PIPX_FETCH_PYTHON=always``) without ``--python`` no longer fails every command with
"requires a Python version"; pipx uses the default Python and fetches only when the package needs a version no local
interpreter has, as documented.
