Keep ``pipx reinstall-all``, ``upgrade-all``, and ``install-all`` waiting for the environments they change when pipx
can no longer write their output, as with ``pipx reinstall-all 2>&1 | head`` or a closed stderr. pipx used to log a
traceback and return while it still rebuilt environments in the background, so an interrupt then skipped the rollback,
and an environment waiting for its turn hung.
