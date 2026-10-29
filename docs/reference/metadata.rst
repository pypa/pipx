##################
 On-disk metadata
##################

pipx has no user configuration file. You configure it only through :doc:`environment variables
<environment-variables>`. The only per-installation state pipx keeps is a metadata file inside each managed virtual
environment.

Every environment under ``$PIPX_HOME/venvs/<environment>/`` holds a ``pipx_metadata.json`` file. pipx writes it after
each operation and reads it to drive ``list``, ``upgrade``, ``reinstall``, ``uninstall``, and the rest. Treat it as
pipx-owned; pipx rewrites it atomically and may change its shape between versions. pipx puts the file back after each
installer run, including ``pipx runpip``, so a wheel's data file of the same name cannot replace it.

pipx masks passwords and tokens in URLs it prints or logs, but keeps ``package_or_url`` and ``pip_args`` here as given,
since ``reinstall`` and ``upgrade`` need them. Those credentials stay in plain text in this file and in the ``pipx list
--json`` snapshot, so prefer a keyring or a ``.netrc`` file over credentials embedded in a URL. pipx writes the file
readable by its owner only, whatever the umask; for a ``--global`` environment that owner is root.

The current schema version is ``0.12`` (``pipx_metadata_version``). pipx migrates older files forward on read.

******************
 Top-level fields
******************

.. list-table::
    :header-rows: 1
    :widths: 30 70

    - - Field
      - Meaning
    - - ``pipx_metadata_version``
      - Schema version string, currently ``"0.12"``.
    - - ``environment``
      - The environment (venv) name, or ``null``.
    - - ``main_package``
      - Package record for the installed application (see below).
    - - ``injected_packages``
      - Map of injected package name to its package record.
    - - ``python_version``
      - Python version the environment was created with, or ``null``.
    - - ``source_interpreter``
      - Path to the interpreter used to create the environment, or ``null``. For an interpreter inside another
        virtual environment, such as an activated bootstrap's ``python3``, pipx records the base interpreter that
        environment's ``pyvenv.cfg`` names, or ``null`` when it names none that exists.
    - - ``venv_args``
      - Extra arguments passed when the venv was created. pipx records only ``--system-site-packages``, and drops
        any other value with a warning when it reads the file.
    - - ``backend``
      - Backend that manages the environment, ``pip`` or ``uv``. pipx reads an unknown value back as ``pip``, with a
        warning.
    - - ``exposure_enabled``
      - Whether pipx currently exposes the environment's apps and man pages on ``PATH``.

*****************
 Package records
*****************

``main_package`` and each entry in ``injected_packages`` share this shape:

.. list-table::
    :header-rows: 1
    :widths: 34 66

    - - Field
      - Meaning
    - - ``package``
      - Canonical package name, or ``null``.
    - - ``package_or_url``
      - The install source as given: a package name, path, or URL.
    - - ``package_version``
      - Resolved installed version.
    - - ``pip_args``
      - Arguments forwarded to the backend at install time, replayed by later ``upgrade`` and ``reinstall`` runs. pipx
        reads them as `pip <https://pip.pypa.io>`_ does and stores each option under its full name, so it stores a
        clustered ``-qf wheels`` as ``-q -f wheels`` and an abbreviated ``--find-l wheels`` as ``--find-links wheels``.
        It stores a relative path given to a pip option, such as ``--cert ca.pem`` or ``--find-links wheels``, as an
        absolute path, and resolves a relative one already on file against the environment's directory.

        Options naming a one-shot input or an output location (``-r``/``--requirement``,
        ``--requirements-from-script``, ``--group``, ``--report``, ``--log``, ``--log-file``, ``--local-log``,
        ``--cache-dir``, ``-t``/``--target``, ``--prefix``, ``--root`` and ``--src``) apply only to the command they
        were given on, so pipx neither stores nor replays them. An abbreviation the current pip finds ambiguous but an
        older pip reads as one of these, such as ``--requirem`` before pip added ``--requirements-from-script``, counts
        as that option, and one that could name a source option goes through the replay check below.

        On POSIX, a replay stops with an error before the installer runs when a stored ``-f``/``--find-links``,
        ``-c``/``--constraint``, ``--build-constraint``, ``--cert``, ``--client-cert``, `uv
        <https://docs.astral.sh/uv/>`_'s ``--config-file``, ``--project``, ``--directory``,
        ``--overrides``/``--override`` or ``--excludes``/``--exclude``, or ``file://`` or local-path index URL names a
        path another account could change, because it or a directory above it is writable by others or owned by another
        user. The record stays as it is; passing the options again with ``--pip-args`` uses them for that run. ``pipx
        list --outdated`` reports such an environment as failed rather than checking it against that path.
    - - ``include_dependencies``
      - Whether pipx exposes apps and man pages from all dependencies.
    - - ``include_resources_from``
      - Dependencies whose apps and man pages pipx exposes individually.
    - - ``include_apps``
      - Whether pipx exposes this package's own apps. Always true for ``main_package``.
    - - ``apps`` / ``app_paths``
      - App names and their paths inside the environment.
    - - ``apps_of_dependencies`` / ``app_paths_of_dependencies``
      - Apps contributed by dependencies, and their paths keyed by dependency.
    - - ``man_pages`` / ``man_paths``
      - Man page names and their paths inside the environment.
    - - ``man_pages_of_dependencies`` / ``man_paths_of_dependencies``
      - Man pages contributed by dependencies, and their paths keyed by dependency.
    - - ``completions`` / ``completion_paths``
      - Shell completion names and their paths inside the environment.
    - - ``completions_of_dependencies`` / ``completion_paths_of_dependencies``
      - Completions contributed by dependencies, and their paths keyed by dependency.
    - - ``expected_apps``
      - Apps required after install via ``--app``.
    - - ``lock_file``
      - Path to the ``pylock.toml`` used to install, or ``null``.
    - - ``cooldown_days``
      - Index-artifact cooldown recorded for the install, from ``--cooldown`` or ``PIPX_COOLDOWN``, or ``null``.
    - - ``suffix``
      - Suffix appended to the environment and executable names, or empty.
    - - ``pinned``
      - Whether the package is pinned against upgrades.

.. note::

    pipx encodes path values as ``{"__type__": "Path", "__Path__": "<path>"}`` so it can round-trip them across
    platforms. The same snapshot, wrapped under ``pipx_spec_version`` and a ``venvs`` map whose entries nest it under a
    ``metadata`` key, is what ``pipx list --output json`` emits and ``pipx install-all`` consumes (see
    :doc:`json-output`).
