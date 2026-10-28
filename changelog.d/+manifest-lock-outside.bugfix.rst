Refuse to run ``pipx manifest lock`` when a tool's ``lock`` path resolves outside the manifest directory, instead of
replacing a ``pylock.toml`` elsewhere on disk and discarding its previous contents. ``pipx manifest sync`` still reads
such locks.
