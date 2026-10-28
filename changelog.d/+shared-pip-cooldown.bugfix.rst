Apply ``--cooldown`` and ``PIPX_COOLDOWN`` to the shared pip that the pip backend installs or refreshes during the
command. pipx used to fetch the newest pip, even one uploaded minutes earlier, while it held back the package itself. A
new shared environment now starts from the oldest pip pipx supports and upgrades only to a release older than the
cooldown.
