``pipx reinstall``, ``pipx reinstall-all`` and ``pipx repair`` now refuse an environment whose ``pipx_metadata.json``
is unreadable or was lost to a killed install, instead of rebuilding it from the default index under the directory
name. ``pipx install`` marks the environment unfinished until it writes the record, and ``pipx uninstall`` moves the
environment to its trash before deleting it, so a killed uninstall no longer leaves a venv without its record.
