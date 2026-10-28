For an editable install, pipx now copies only the man pages that resolve inside the project directory. Before, it
followed absolute paths, ``..`` and symlinks, and a wheel installed by name could ship its own editable
``direct_url.json`` to make pipx copy any readable file into the environment and link it as a man page.
