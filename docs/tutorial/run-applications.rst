#####################
 Running applications
#####################

``pipx run`` downloads and runs a Python application in a one-time, temporary environment, then leaves your system
untouched. Reach for it to scaffold a new project, check an app's help text, or try a tool without committing to an
install.

*************
 Basic usage
*************

.. code-block:: console

    $ pipx run pycowsay moo

pipx installs the package in an isolated, temporary directory and invokes the app:

.. code-block:: console

    $ pipx run pycowsay moo
      ---
    < moo >
      ---
       \   ^__^
        \  (oo)\_______
           (__)\       )\/\
               ||----w |
               ||     ||

Arguments after the app name pass straight through to it:

.. code-block:: console

    $ pipx run pycowsay these arguments all go to pycowsay

*********************
 Ambiguous arguments
*********************

pipx can swallow an argument meant for the app when it looks like one of pipx's own options:

.. code-block:: console

    $ pipx run pycowsay --py
    pipx run: error: ambiguous option: --py could match --python-args, --pypackages, --python

Put ``--`` before the app name to forward everything after it verbatim:

.. code-block:: console

    $ pipx run -- pycowsay --py

**********************************
 When the app name differs
**********************************

Some packages expose an app under a different name, or expose several. Use ``--spec`` to name the package and the app
separately:

.. code-block:: console

    $ pipx run --spec PACKAGE APP

`esptool <https://github.com/espressif/esptool>`_, for example, lists its executables when you guess wrong:

.. code-block:: console

    $ pipx run esptool
    'esptool' executable script not found in package 'esptool'.
    Available executable scripts:
        esptool.py - usage: 'pipx run --spec esptool esptool.py [arguments?]'
        espefuse.py - usage: 'pipx run --spec esptool espefuse.py [arguments?]'

Run the one you want with ``--spec``:

.. code-block:: console

    $ pipx run --spec esptool esptool.py

Package authors can remove this requirement by declaring a :doc:`pipx.run entry point
<../explanation/making-packages-compatible>` in their metadata.

.. _tutorial-run-cache:

***********
 Run cache
***********

pipx caches each ``pipx run`` environment for a few days so repeated runs start instantly. After the cache expires, the
next run fetches the latest version.

.. mermaid::

    flowchart LR
        RUN["pipx run APP"] --> CHECK{"cached?"}
        CHECK -->|"no"| FETCH["fetch + build venv"]
        FETCH --> CACHE["cache venv"]
        CHECK -->|"yes"| REUSE["reuse cached venv"]
        CACHE --> REUSE
        REUSE --> EXPIRE["expires after a few days"]
        EXPIRE --> RUN

        classDef step fill:#2a9d8f,stroke:#1f7268,color:#fff;
        classDef decide fill:#c78c20,stroke:#946716,color:#fff;
        class RUN,FETCH,CACHE,REUSE,EXPIRE step;
        class CHECK decide;

Force a rebuild before the cache expires with ``--refresh``, which replaces that app's cached environment and keeps the
replacement:

.. code-block:: console

    $ pipx run --refresh APP

``--no-cache`` also rebuilds, but marks the new environment for cleanup by a later run. The two options are mutually
exclusive.

Inspect or clear every cached run environment:

.. code-block:: console

    $ pipx cache dir
    $ pipx cache purge

For how pipx decides what to cache and when, see :doc:`How pipx works <../explanation/how-pipx-works>`.

************
 Learn more
************

- :doc:`Use the uv backend <../how-to/use-uv-backend>`: run with uv, which keeps its own ephemeral cache.
- :doc:`../reference/cli`: every ``pipx run`` flag, including ``--python-args`` and ``--with``.
