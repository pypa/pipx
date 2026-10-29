``pipx reinstall pipx`` on a pipx that manages itself no longer crashes with an ``ImportError`` when it installs a
different pipx version. Modules the running pipx imported late came from the version it was installing, so old and new
code mixed. It now loads them from its own moved environment, which the next pipx command deletes from the trash.
