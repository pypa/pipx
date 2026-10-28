Report an environment whose ``pipx_metadata.json`` the current user cannot read as unreadable in ``pipx list``,
instead of as missing metadata from a pipx older than 0.15 that needs reinstalling. This is what a non-root user sees
for every environment of ``pipx list --global``: pipx keeps the file owner-only because it can hold index credentials.
Environments the user can read are still listed.
