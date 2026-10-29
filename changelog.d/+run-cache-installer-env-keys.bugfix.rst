``pipx run`` now keys its cache only on the ``PIP_*`` and ``UV_*`` variables that change what the installer resolves or
installs, such as index URLs, find-links, constraints, pre-release and binary policy, upload cutoffs and config files. It
keyed on every variable with those prefixes, so a timeout, verbosity or cache directory setting, or the
``UV_RUN_RECURSION_DEPTH`` that ``uv run`` sets for its children, rebuilt the environment for an unchanged command.
