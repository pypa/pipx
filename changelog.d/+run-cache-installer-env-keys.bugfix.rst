``pipx run`` no longer keys its cache on the ``PIP_*`` and ``UV_*`` variables that cannot change what the installer
resolves or installs: timeouts, retries, parallelism, verbosity, progress and color output, cache directories, and the
``UV_RUN_RECURSION_DEPTH`` that ``uv run`` sets for its children. Setting one of them rebuilt the environment for an
unchanged command. Every other variable with those prefixes stays in the key, whatever its case or ``-``/``_``
spelling, since pip reads ``PIP_index_url`` the same as ``PIP_INDEX_URL``.
