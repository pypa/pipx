The pip backend now removes ``pip.conf`` (``pip.ini`` on Windows) from the root of an environment before it starts
pip there. A wheel could ship that file as a data file, and pip read it as its site configuration, so a ``target`` or
index in it made a later ``pipx upgrade`` or ``pipx inject`` install outside the environment or from another index.
