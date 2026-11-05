``pipx repair`` no longer skips environments whose ``pipx_metadata.json`` a killed install lost or this user cannot
read; like ``pipx reinstall`` and ``pipx reinstall-all``, it refuses them instead of reporting them healthy.
