pipx now reads a package's ``entry_points.txt`` only when that package's ``RECORD`` lists it, or when the package has
no ``RECORD``. A dependency could ship that file into the ``.dist-info`` of a main package that has no entry points of
its own and get its apps exposed without ``--include-deps``.
