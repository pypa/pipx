Report an environment whose ``pipx_metadata.json`` the current user cannot read as unreadable in ``pipx list``,
instead of as missing metadata from a pipx older than 0.15 that needs reinstalling. A non-root user sees this for every
environment of ``pipx list --global``, because pipx keeps the file owner-only: it can hold index credentials.
``pipx list`` still lists the environments the user can read.
