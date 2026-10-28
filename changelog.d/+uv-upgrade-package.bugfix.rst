Under the uv backend, ``pipx upgrade``, ``upgrade-all`` and ``install --upgrade`` now pass uv ``--upgrade-package NAME``
instead of ``--upgrade``, so they upgrade only the named package and leave its dependencies alone unless the new
release needs others, as pip's default ``only-if-needed`` strategy does. Before, uv upgraded every dependency, replacing
packages injected with ``pipx inject --force`` and pinned with ``pipx pin --injected-only``.
