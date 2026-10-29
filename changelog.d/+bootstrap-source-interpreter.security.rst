pipx no longer records an interpreter that lives inside another virtual environment, such as the ``python3`` of an
activated bootstrap environment or of one made with ``python3 -m venv --copies``. It records the base interpreter named
in that environment's ``pyvenv.cfg``, which outlives the bootstrap. ``pipx install-all`` also stops building on an
exported interpreter that sits inside a virtual environment or that another account can change, and uses the default
Python with a message instead, so a snapshot taken before the bootstrap was removed no longer runs whatever another
account later puts at its old path.
