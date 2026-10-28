``pipx uninject`` now ignores installed distributions whose metadata ``Name`` is not a valid project name when it looks
for orphaned dependencies to remove. A name such as ``-t/some/dir`` or ``-rFILE`` reached ``uv pip uninstall`` or
``pip uninstall`` as an option, and with uv could delete packages from a directory outside pipx.
