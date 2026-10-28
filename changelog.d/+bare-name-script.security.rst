A bare package name such as ``pipx install pycowsay`` now always means the package on the index. A file of that name
without a suffix in the working directory no longer gets installed as a PEP 723 script; pass a path such as
``./pycowsay`` to install one. URL specs no longer pick up a script at the matching relative path below the working
directory either.
