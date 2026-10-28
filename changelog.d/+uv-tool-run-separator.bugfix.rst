Under the uv backend, ``pipx run`` now puts ``--`` before the app name it hands to ``uv tool run``. An app word that
started with a single dash, such as ``pipx run -- -ihttp://host/simple demodep``, was read by uv as one of its own
options, and uv installed and ran the next word as the package.
