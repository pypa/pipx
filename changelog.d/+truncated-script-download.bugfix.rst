``pipx run`` and ``pipx install`` now fail when a script download ends before its ``Content-Length``. Before, pipx ran
or installed the part that arrived and could exit 0.
