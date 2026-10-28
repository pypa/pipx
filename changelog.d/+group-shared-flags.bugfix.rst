Reject ``--global``, ``--skip-maintenance``, ``--verbose`` and ``--quiet`` placed between ``manifest``,
``interpreter`` or ``cache`` and their subcommand, as in ``pipx manifest --global sync``. pipx accepted the option there
and then dropped it, so ``pipx manifest --global sync --prune`` synced and pruned the per-user store with exit 0. Put
the option after the subcommand, as in ``pipx manifest sync --global``.
