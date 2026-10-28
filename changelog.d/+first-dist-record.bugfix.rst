When an environment holds two ``.dist-info`` records with the same name, pipx now reads the first one on ``sys.path``,
the one the environment's interpreter uses. Since 1.15.1 it read the last one, so ``--system-site-packages`` with a
different version of the package in the base interpreter reported that version and exposed its commands.
