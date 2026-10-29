A pipx that changed its own environment, through ``pipx upgrade pipx`` or ``pipx reinstall pipx`` for example, no longer
crashes with an ``ImportError`` when another pipx command empties the trash while it is still running, such as during
the rest of ``pipx upgrade-all``. The copy of its environment it imports from now stays in the trash until the process
exits.
