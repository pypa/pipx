#############
 JSON output
#############

Most pipx commands accept ``--output json`` to print a single machine-readable result envelope on stdout instead of
human-readable text. Selecting JSON suppresses pipx's own progress messages and sends whatever pip or uv print while
installing to stderr, so the envelope is the only thing on stdout.

**********
 Envelope
**********

The envelope is a JSON object with these keys (serialized with sorted keys):

.. list-table::
    :header-rows: 1
    :widths: 26 74

    - - Key
      - Value
    - - ``pipx_result_version``
      - Envelope schema version, currently ``"1"``.
    - - ``command``
      - The command tokens as a list, for example ``["install"]`` or ``["cache", "dir"]``.
    - - ``status``
      - ``"success"`` when there are no errors, ``"partial"`` when the run both succeeded somewhere and recorded
        errors, ``"error"`` otherwise.
    - - ``exit_code``
      - The integer process exit code (see :doc:`exit-codes`).
    - - ``data``
      - Command-specific payload object. Its fields depend on the command.
    - - ``errors``
      - List of error objects. Each has ``code``, ``message``, and the optional identity fields ``environment`` and
        ``package``.

.. code-block:: json

    {
      "pipx_result_version": "1",
      "command": ["install"],
      "status": "success",
      "exit_code": 0,
      "data": {},
      "errors": []
    }

Once the arguments parse, a failure on a JSON-enabled command still speaks the envelope. That covers an invalid
environment variable such as ``PIPX_COOLDOWN``, a ``--python`` that cannot be resolved, a path or URL where a package
name belongs, and ``--backend uv`` without a ``uv`` executable. The envelope has a ``status`` of ``"error"`` and a
single error whose ``code`` is ``pipx_error``, and pipx exits ``1``. Only argument-parsing errors, such as an unknown
option or a missing argument, print plain text instead: the usage message goes to stderr and pipx exits ``2``.

********************
 Supported commands
********************

``--output json`` is available on: ``install``, ``inject``, ``uninject``, ``expose``, ``unexpose``, ``pin``,
``unpin``, ``upgrade``, ``upgrade-all``, ``upgrade-shared``, ``uninstall``, ``uninstall-all``, ``reinstall``,
``reinstall-all``, ``reset``, ``health``, ``repair``, ``manifest lock``, ``manifest sync``, ``interpreter list``,
``interpreter prune``, ``interpreter upgrade``, ``cache dir``, ``cache purge``, and ``list --outdated``.

It is not available on ``install-all``, ``run``, ``exec``, ``runpip``, ``ensurepath``, ``environment``,
``completions``, or ``help``.

***********************
 ``list`` is different
***********************

``pipx list --output json`` without ``--outdated`` does not emit the result envelope; errors still use it. It prints
the installed-package snapshot that ``install-all`` reads back: an object with ``pipx_spec_version`` (currently
``"0.1"``) and a ``venvs`` map of environment name to an object whose ``metadata`` key holds that environment's metadata
(see :doc:`metadata`). ``pipx list --json`` is a legacy alias for the same snapshot.

.. code-block:: console

    $ pipx list --output json > pipx.json
    $ pipx install-all pipx.json

``--json`` is a legacy alias only on ``list``; every other command uses ``--output json``.
