Stop ``pipx upgrade-all`` from moving an app, manual page, or completion that two environments expose to the other
environment while the installer of its owner is replacing the linked file. pipx treated any link whose target was
missing as left over and replaced it without ``--force``; a missing target inside another environment that still exists
now counts as a collision.
