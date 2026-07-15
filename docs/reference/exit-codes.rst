############
 Exit codes
############

pipx returns ``0`` on success and ``1`` on failure. A command that raises an unexpected error, is interrupted, or hits
an argument-parsing problem also exits non-zero. The named codes below come from ``pipx.constants``; each maps to one of
those two process exit values.

.. list-table::
    :header-rows: 1
    :widths: 12 48 40

    - - Code
      - Name
      - Meaning
    - - ``0``
      - ``EXIT_CODE_OK``
      - Command completed successfully.
    - - ``0``
      - ``EXIT_CODE_INSTALL_VENV_EXISTS``
      - Install skipped because the environment already exists; not treated as a failure.
    - - ``1``
      - ``EXIT_CODE_INJECT_ERROR``
      - ``inject`` failed to install one or more packages.
    - - ``1``
      - ``EXIT_CODE_UNINJECT_ERROR``
      - ``uninject`` failed to remove one or more packages.
    - - ``1``
      - ``EXIT_CODE_LIST_PROBLEM``
      - ``list`` found an environment it could not read.
    - - ``1``
      - ``EXIT_CODE_UNINSTALL_VENV_NONEXISTENT``
      - ``uninstall`` targeted an environment that does not exist.
    - - ``1``
      - ``EXIT_CODE_UNINSTALL_ERROR``
      - ``uninstall`` failed to remove the environment.
    - - ``1``
      - ``EXIT_CODE_REINSTALL_VENV_NONEXISTENT``
      - ``reinstall`` targeted an environment that does not exist.
    - - ``1``
      - ``EXIT_CODE_REINSTALL_INVALID_PYTHON``
      - ``reinstall`` was given a Python interpreter it could not use.
    - - ``1``
      - ``EXIT_CODE_SPECIFIED_PYTHON_EXECUTABLE_NOT_FOUND``
      - The interpreter passed to ``--python`` was not found.
