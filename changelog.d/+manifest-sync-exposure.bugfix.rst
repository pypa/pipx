Keep the apps, manual pages, and completions of injected packages exposed when ``pipx manifest sync`` reinstalls an
existing environment, and expose the environment again when the sync is interrupted. pipx used to drop those links
without a message, so another package could take the freed names without ``--force``, and an interrupted sync left the
rolled-back environment unexposed.
