############
 Exit codes
############

pipx returns ``0`` on success and ``1`` on failure. ``run``, ``runpip``, and ``exec`` exit with the code of the app or
pip they ran, and argument-parsing errors exit ``2``. A command that raises an unexpected error or is interrupted also
exits non-zero. The named codes below come from ``pipx.constants``; each maps to ``0`` or ``1``.

``reinstall-all`` exits with ``1`` if any environment could not be reinstalled,
including when its selected Python interpreter belongs to that environment.
With ``--output json``, failed environments appear in ``errors`` and only
successfully reinstalled environments appear in ``data.environments``.

.. list-table::
    :header-rows: 1
    :widths: 12 48 40

    - - Code
      - Name
      - Meaning
    - - ``0``
      - ``EXIT_CODE_OK``
      - Command completed successfully.
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
      - ``reinstall`` selected a Python interpreter that lives inside the environment being reinstalled.
    - - ``1``
      - ``EXIT_CODE_SPECIFIED_PYTHON_EXECUTABLE_NOT_FOUND``
      - The interpreter passed to ``--python`` was not found.
