When ``pipx install --force`` or ``pipx manifest sync`` rebuilds an existing environment, either on another Python
because the release's ``Requires-Python`` rules out the current one or to apply a lock file, keep the backend recorded
for that environment. The rebuild used to pick the backend as for a new environment, so a pip-backed environment could
move to uv and install from uv's default index instead of the one set in ``PIP_INDEX_URL`` or ``pip.conf``.
