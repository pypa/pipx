Leave a command, man page or completion that the environment did not expose before with its owner when ``pipx
reinstall``, ``reinstall-all``, ``interpreter upgrade``, the repair step of ``pipx upgrade``, or a repeated ``pipx
manifest sync`` rebuilds the environment. These used to replace such a file as if ``--force`` had been passed, deleting
a user's own script or repointing another environment's command, although ``pipx install`` had left it alone with a
warning. A name two environments both declare now stays with the one that held it, instead of going to whichever
``reinstall-all`` rebuilt last.
