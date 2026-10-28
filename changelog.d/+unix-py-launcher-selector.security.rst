Ask the Python Launcher for Unix for a ``--python`` value only when it is an ``X`` or ``X.Y`` version. The launcher
ran any other value, such as ``3.14.8`` or ``3.13t``, on the first interpreter its search found, which could be a
``.venv`` in a parent of the current directory.
