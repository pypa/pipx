Resolve every relative path given to a pip option, such as ``--cert ca.pem``, ``-r requirements.txt``, ``--log`` or
``--cache-dir``, against the directory pipx was started in, also when the option is clustered or abbreviated, as in
``-qr requirements.txt`` or ``--find-l wheels``. The shared pip refresh runs inside the shared libraries directory, so
``pipx upgrade-shared --pip-args='--cert=ca.pem'`` failed with ``invalid path: ca.pem``; installs, upgrades and ``pipx
run`` now also resolve these values against the starting directory.
