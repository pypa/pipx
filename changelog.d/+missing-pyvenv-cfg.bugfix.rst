Refuse to run pip or uv in an environment whose ``pyvenv.cfg`` is gone, and suggest ``pipx reinstall``. Without that
file the environment's ``python`` link starts the interpreter it was created from, so a ``pipx upgrade`` after a wheel
had shipped and then dropped ``pyvenv.cfg`` installed the package into that interpreter's prefix and reported success.
