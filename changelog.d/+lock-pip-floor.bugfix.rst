Refuse ``pipx install --lock`` and ``pipx manifest sync`` with a lock under the pip backend when the environment's pip
is older than 26.1. That pip read ``pylock.toml`` as a requirements file: a real lock failed with a confusing
``Invalid requirement`` error, and a file that was not a lock had its lines applied as pip options. The error now
names the pip version and suggests ``pipx upgrade-shared``.
