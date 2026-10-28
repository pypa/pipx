pipx now adds ``-E`` to an app script's shebang by writing a new file and renaming it over the script, instead of
writing into the existing file. With the uv backend the script can be a hard link or symlink into uv's cache, so the
in-place write also changed the cache entry and the same script in every other environment uv had installed that wheel
into.
