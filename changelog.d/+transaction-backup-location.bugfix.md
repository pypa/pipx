Keep the backups that `install --force` and `reinstall` take while replacing an environment in pipx's trash rather than
beside the live environments. A backup placed in the venvs directory was picked up as a broken environment by a
concurrent `list` or `reinstall-all`; the trash shares the home's filesystem, so restoring a backup is still an atomic
rename.
