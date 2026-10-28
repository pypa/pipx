Restore the existing environment when ``pipx install --force`` or ``pipx install-all --force`` rebuilds it on another
interpreter because of the package's ``Requires-Python`` and the rebuild fails. pipx used to delete the environment
first and leave behind an empty one without its app, injected packages, or ``pipx_metadata.json``, while it reported it
had kept the environment. It now moves the environment to its trash before the rebuild and moves it back on failure.
