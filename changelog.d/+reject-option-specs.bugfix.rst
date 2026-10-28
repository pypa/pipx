``pipx install --preinstall`` and ``pipx run --with`` now refuse a value that starts with ``-``. Written as
``--with=--find-links=DIR`` or ``--preinstall=-rFILE``, such a value reached pip or ``uv pip install`` as an installer
option and changed where packages came from, instead of failing like the main package spec does. Pass installer options
with ``--pip-args``.
