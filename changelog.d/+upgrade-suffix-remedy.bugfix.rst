``pipx upgrade`` now keeps ``--suffix`` in the reinstall command it suggests for an environment installed from a
local source, instead of printing a name that pipx reads as a URL.
The ``upgrade`` and ``upgrade-all`` JSON payloads now report the environment ``suffix`` alongside the package name.
