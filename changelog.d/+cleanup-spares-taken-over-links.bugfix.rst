Keep a command, man page or completion link that another package took over while ``pipx reinstall``,
``reinstall-all``, ``uninject`` or ``uninstall-all`` was running. These commands gathered the environment's links first
and deleted them by name later, so a name another package claimed in between, for example in the same parallel
``reinstall-all``, disappeared without a message. pipx now deletes a link only if it still points into the environment.
