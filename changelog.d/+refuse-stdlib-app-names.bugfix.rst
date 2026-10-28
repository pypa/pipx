pipx no longer exposes an app whose name is a standard library module or ``pipx`` plus an import suffix, such as
``enum.py``, ``re.pyc`` or ``pipx.py``, or a directory named after one, and warns instead. Python searches the directory
of the script it starts first, so in ``~/.local/bin`` such an app replaced the module for pip's ``pipx`` launcher, which
imports ``re`` and then ``pipx`` before pipx can drop that directory from ``sys.path``, and for every other Python
script installed there.
