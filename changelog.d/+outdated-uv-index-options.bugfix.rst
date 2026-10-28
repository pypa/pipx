``pipx list --outdated`` and ``pipx upgrade-all`` now check uv environments against the index recorded with uv's
option names (``--default-index``, ``--index``, ``--allow-insecure-host``, ``--index-strategy``,
``--keyring-provider``) instead of uv's default index.
