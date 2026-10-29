``pipx upgrade pipx``, ``pipx upgrade-all`` and ``pipx install --force pipx`` on a pipx that manages itself no longer
crash with an ``ImportError`` when they install a different pipx version. The running pipx now loads its late imports
from a copy of its environment, which the next pipx command deletes from the trash.
