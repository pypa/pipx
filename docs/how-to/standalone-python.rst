##################
 Standalone Python
##################

Install an app under a Python interpreter downloaded from `python-build-standalone
<https://github.com/astral-sh/python-build-standalone>`_ instead of the system one. Reach for this when the system
Python lacks the version you need, or when a distro patched its Python in ways that break the app.

*****************
 How pipx decides
*****************

``--fetch-python`` (or ``PIPX_FETCH_PYTHON``) sets the policy. Without ``--python``, pipx first looks for a local
interpreter that satisfies the app's ``requires-python``, and the policy only decides what happens when none does:

.. mermaid::

    flowchart TD
        START["pipx install"] --> DEF{"default Python satisfies<br/>requires-python?"}
        DEF -->|yes| USEDEF["use default Python"]
        DEF -->|no| SEARCH{"another local<br/>interpreter fits?"}
        SEARCH -->|yes| USEMATCH["use newest match"]
        SEARCH -->|no| POLICY{"--fetch-python"}
        POLICY -->|never| FAIL["error"]
        POLICY -->|missing or always| FETCH["download standalone build"]

        classDef decision fill:#2a9d8f,stroke:#1f7268,color:#fff;
        classDef fetch fill:#c78c20,stroke:#946716,color:#fff;
        classDef use fill:#388e3c,stroke:#276628,color:#fff;
        classDef fail fill:#c62828,stroke:#8e1c1c,color:#fff;
        class POLICY,DEF,SEARCH decision;
        class FETCH fetch;
        class USEDEF,USEMATCH use;
        class FAIL fail;

Naming ``--python`` yourself keeps the last word: pipx uses the interpreter you named and reports it, rather than
overriding you when the package rejects it.

***************
 Set the policy
***************

.. list-table::
    :header-rows: 1
    :widths: 20 80

    - - Value
      - Behavior
    - - ``never``
      - Default. Never download; use interpreters from ``PATH`` or the ``py`` launcher.
    - - ``missing``
      - Look locally first; download when the requested version is not found.
    - - ``always``
      - Skip the local search and use a standalone build for the version named with ``--python``.

.. code-block:: console

    $ pipx install --python 3.13 --fetch-python=missing my-package
    $ pipx install --python 3.13 --fetch-python=always my-package

Set it for the whole shell session with the environment variable:

.. code-block:: console

    $ export PIPX_FETCH_PYTHON=missing
    $ pipx install --python 3.13 my-package

Reach for ``always`` in CI runs that should not depend on the runner's Python, on distros that strip modules like
``tkinter`` or ``lzma``, or on air-gapped hosts with a populated standalone cache.

***************************
 Manage cached interpreters
***************************

pipx unpacks each interpreter into its standalone cache. Manage them with:

.. code-block:: console

    $ pipx interpreter list
    $ pipx interpreter prune
    $ pipx interpreter upgrade

.. note::

    ``--fetch-missing-python`` and ``PIPX_FETCH_MISSING_PYTHON`` still work but are deprecated aliases for
    ``--fetch-python=missing`` / ``PIPX_FETCH_PYTHON=missing``. pipx errors if you set both
    ``PIPX_FETCH_MISSING_PYTHON`` and ``PIPX_FETCH_PYTHON``.

**********
 Verify it
**********

.. code-block:: console

    $ pipx list

The environment lists the interpreter version pipx settled on. For how pipx resolves interpreters, see
:doc:`../explanation/how-pipx-works`.
