###################
 Use the uv backend
###################

Make pipx use `uv <https://github.com/astral-sh/uv>`_ to create virtual environments and install packages in place of
pip and venv. The CLI surface stays the same.

For why uv is faster and how pipx compares to Astral's standalone ``uv tool``, see :doc:`../explanation/comparisons`.

******************
 Make uv available
******************

Install pipx with the ``uv`` extra so it ships the bundled binary:

.. code-block:: console

    $ pipx install pipx[uv]

Or install uv however you like (``brew install uv``, ``cargo install uv``) and put it on ``PATH``; pipx picks it up
automatically. New venvs then default to uv. Existing venvs keep their recorded backend.

*************************
 How pipx picks a backend
*************************

.. mermaid::

    flowchart TD
        START["new venv"] --> CLI{"--backend given?"}
        CLI -->|yes| USECLI["use it"]
        CLI -->|no| ENV{"PIPX_DEFAULT_BACKEND set?"}
        ENV -->|yes| USEENV["use it"]
        ENV -->|no| UV{"uv available?<br/>bundled or on PATH"}
        UV -->|yes| USEUV["uv"]
        UV -->|no| PIP["pip + venv"]

        classDef decision fill:#2a9d8f,stroke:#1f7268,color:#fff;
        classDef uv fill:#7c4dff,stroke:#5a34c0,color:#fff;
        classDef pip fill:#3f72af,stroke:#28507d,color:#fff;
        class CLI,ENV,UV decision;
        class USECLI,USEENV,USEUV uv;
        class PIP pip;

****************************
 Choose a backend explicitly
****************************

.. code-block:: console

    $ pipx install black --backend pip
    $ pipx install ruff --backend uv
    $ PIPX_DEFAULT_BACKEND=uv pipx install ruff
    $ pipx environment --value PIPX_RESOLVED_BACKEND

``install``, ``install-all``, ``inject``, ``upgrade``, ``upgrade-all``, ``reinstall``, ``reinstall-all``, and ``run``
all accept ``--backend``. Switch an installed venv with ``pipx reinstall NAME --backend uv``.

**********************
 What changes under uv
**********************

- pipx creates venvs with ``uv venv``. The venv contains no ``pip`` and no ``pipx_shared.pth`` file.
- ``pipx runpip`` runs ``uv pip <args> --python <venv>/bin/python``. uv rejects flags it does not understand rather than
  dropping them silently.
- ``pipx run`` execs ``uv tool run``; its cache lives in uv's cache directory. Pass ``--no-cache`` to skip it or
  ``--refresh`` to rebuild the cached environment.
- ``pipx run script.py`` execs ``uv run --script script.py`` for PEP 723 inline scripts.
- ``--cooldown DAYS`` maps to uv's ``--exclude-newer P{DAYS}D``. Relative cooldowns need uv 0.9.17 or newer.

************
 Limitations
************

- ``pipx install pip --backend uv`` errors: a uv venv has no pip. Use ``--backend pip``.
- ``pipx run --backend uv`` does not honor ``[pipx.run]`` entry points; ``uv tool run`` sees only standard console
  scripts. Use ``--backend pip`` when your package declares them.
- Some ``--pip-args`` values have no ``uv tool run`` equivalent (``--editable``, ``--no-build-isolation``); pipx errors
  instead of dropping them. See :doc:`use-private-index` for which flags uv translates.
- ``pipx run --backend uv`` against URL or named-pipe scripts falls back to a pipx-managed venv, because ``uv run
  --script`` reads PEP 723 metadata off disk and runtime-fetched content has no on-disk path. pipx logs a warning.

*************
 Cache layout
*************

Under the uv backend, ``pipx run`` caches in ``UV_CACHE_DIR`` instead of ``PIPX_VENV_CACHEDIR``. Switching the default
backend on a host that already used ``pipx run`` leaves the old pipx cache behind. Find it with ``pipx cache dir`` and
remove its environments with ``pipx cache purge``. The 14-day expiry sweep pipx applies to its own cache does not extend
to uv's cache, which uv manages on its own schedule (``uv cache clean``).

**********
 Verify it
**********

.. code-block:: console

    $ pipx environment --value PIPX_RESOLVED_BACKEND

It prints ``uv`` when pipx will use the uv backend for new venvs.
