Refuse to overwrite ``/etc/profile.d/pipx.sh`` or ``/etc/paths.d/pipx`` in ``pipx ensurepath --global`` when the file
holds content pipx did not write, such as an administrator's ``PIPX_GLOBAL_HOME`` or ``PIP_INDEX_URL`` exports. pipx
used to replace the whole file with its ``PATH`` entry and report success. It now leaves the file and its mode alone and
exits with an error that names ``--force``, which still replaces the file. pipx replaces a file that holds only an
earlier pipx entry, as before.
