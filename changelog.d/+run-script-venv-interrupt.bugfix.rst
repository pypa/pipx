``pipx run script.py`` now expires its cache entry when creating the environment fails or is interrupted, not only when
installing the script's dependencies does. A Ctrl-C during ``python -m venv`` left an empty cache directory, and every
later run of the script reused it and failed with ``FileNotFoundError`` until the entry expired.
