``pipx reinstall pipx`` on a pipx that manages itself no longer crashes with an ``ImportError`` when PyPI has a newer
pipx. The running pipx kept loading modules it had not loaded yet from the version it was installing, so old and new code
mixed. It now loads them from its own moved environment, and the next pipx command deletes that copy from the trash.
