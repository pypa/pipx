Under the uv backend, ``pipx run script.py`` now keeps the script's environment in pipx's run cache, keyed to the
script's path, the interpreter, ``--pip-args`` and the cooldown. uv kept one environment per script path and reused it
while it satisfied the script, so a changed ``--index-url``, ``--pip-args`` or ``--cooldown``, or ``--refresh``, still
ran what an earlier run installed. ``pipx cache purge`` and the 14-day expiry now cover these environments.
