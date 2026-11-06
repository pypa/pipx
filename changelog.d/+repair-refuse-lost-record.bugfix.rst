``pipx repair`` now refuses an environment whose ``pipx_metadata.json`` a killed install lost or a newer pipx wrote, as
``pipx reinstall`` and ``pipx reinstall-all`` do, instead of reporting it healthy.
