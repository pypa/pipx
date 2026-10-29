Stop ``pipx ensurepath --global --force`` from crashing with ``UnicodeDecodeError`` when ``/etc/profile.d/pipx.sh`` or
``/etc/paths.d/pipx`` holds bytes that are not UTF-8. ``--force`` now replaces the file without reading it, and without
``--force`` such a file gets the same error that names ``--force`` as any other file pipx did not write.
