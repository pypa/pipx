#############
 Comparisons
#############

*************
 pipx vs pip
*************

-  pip is a general Python package installer. It can install libraries or CLI applications with entry points.
-  pipx is a specialized package installer. It can only install packages with CLI entry points.
-  pipx and pip both install packages from PyPI (or locally).
-  pipx relies on pip (and venv).
-  pipx replaces a subset of pip's functionality: it installs CLI applications but not libraries that you import in your
   code.
-  You can install pipx with pip.

Example: install pipx with pip, ``pip install --user pipx``.

*****************
 pipx vs uv tool
*****************

Both `uv tool <https://docs.astral.sh/uv/concepts/tools/>`_ and pipx install a Python tool into its own virtual
environment and expose the tool's console scripts on ``PATH``. Both have a one-shot run mode (``uvx`` and ``pipx run``);
``uvx`` is ``uv tool run``. They differ in where state lives, which extra commands they ship, and how they handle managed
Python.

pipx keeps the same CLI across pip and uv backends; ``pipx install pipx[uv]`` opts you into uv-speed venv creation
without changing any commands. ``uv tool`` ships a smaller per-tool surface, then reuses the rest of ``uv`` for free:
managed Python, content-addressed cache, lockfiles, PEP 723 script handling.

Where state lives
=================

.. list-table::
    :header-rows: 1
    :widths: 24 38 38

    - - State
      - pipx
      - uv tool
    - - Per-tool venvs
      - ``$PIPX_HOME/venvs/<name>`` (``PIPX_HOME``)
      - ``$UV_TOOL_DIR/<name>`` (``UV_TOOL_DIR``)
    - - Exposed binaries
      - ``$PIPX_BIN_DIR`` (default ``~/.local/bin``)
      - ``$UV_TOOL_BIN_DIR`` (default same)
    - - Man pages
      - ``$PIPX_MAN_DIR`` (default ``~/.local/share/man``)
      - *not exposed*
    - - Shared pip/setuptools/wheel
      - ``$PIPX_HOME/shared`` (pip backend only)
      - *none; uv venvs ship without pip*
    - - Ephemeral run cache
      - ``$PIPX_HOME/.cache`` (TTL 14 days)
      - ``$UV_CACHE_DIR`` (no TTL; ``uv cache prune``)
    - - Standalone Python
      - ``$PIPX_HOME/py`` (``PIPX_FETCH_PYTHON``)
      - ``$UV_PYTHON_INSTALL_DIR``
    - - System-wide install
      - ``--global``, ``PIPX_GLOBAL_*``
      - *not supported*

``PIPX_BIN_DIR`` and ``UV_TOOL_BIN_DIR`` both default to ``~/.local/bin`` on Unix, so installing the same tool with both
managers writes the same filename. Each manager refuses to overwrite a binary the other one wrote without ``--force``.
Use ``pipx install --suffix=...`` to keep two copies side-by-side; uv has no equivalent.

Subcommand mapping
==================

.. list-table::
    :header-rows: 1
    :widths: 26 37 37

    - - Task
      - pipx
      - uv tool
    - - Install from PyPI
      - ``pipx install ruff``
      - ``uv tool install ruff`` (or ``uvx ruff`` for one-off)
    - - Install from a git URL
      - ``pipx install 'git+https://…'``
      - ``uv tool install 'git+https://…'``
    - - Install editable from path
      - ``pipx install -e ./mypkg``
      - ``uv tool install -e ./mypkg``
    - - One-off run (no install)
      - ``pipx run black .``
      - ``uvx black .``
    - - Refresh one-off run
      - ``pipx run --refresh black .``
      - ``uvx --refresh black .``
    - - Show ephemeral cache
      - ``pipx cache dir``
      - ``uv cache dir``
    - - Purge ephemeral cache
      - ``pipx cache purge``
      - ``uv cache clean``
    - - One-off run with extra dep
      - ``pipx run --with mkdocs-material mkdocs``
      - ``uvx --with mkdocs-material mkdocs``
    - - Pinned-version one-off
      - ``pipx run --spec 'ruff==0.6.0' ruff check``
      - ``uvx ruff@0.6.0 check``
    - - Add a dep to existing tool
      - ``pipx inject mkdocs mkdocs-material``
      - ``uv tool install mkdocs --with mkdocs-material`` (rebuilds)
    - - Remove an injected dep
      - ``pipx uninject mkdocs mkdocs-material``
      - *rebuild without* ``--with``
    - - Upgrade one
      - ``pipx upgrade ruff``
      - ``uv tool upgrade ruff``
    - - Upgrade all
      - ``pipx upgrade-all``
      - ``uv tool upgrade --all``
    - - List installed or outdated
      - ``pipx list`` (``--outdated``, ``--output json``)
      - ``uv tool list`` (``--show-with``, ``--outdated``, …)
    - - Diagnose broken environments
      - ``pipx health``
      - *no equivalent*
    - - Repair broken environments
      - ``pipx repair ruff`` / ``repair``
      - ``uv tool install ruff`` / *no bulk equivalent*
    - - Reinstall any environment
      - ``pipx reinstall ruff`` / ``reinstall-all``
      - ``uv tool upgrade --reinstall ruff`` / ``--all``
    - - Run pip inside a venv
      - ``pipx runpip <tool> -- pip ...``
      - *not supported (no pip in uv venvs)*
    - - PATH setup
      - ``pipx ensurepath``
      - ``uv tool update-shell``
    - - Show resolved env
      - ``pipx environment``
      - ``uv tool dir``, ``uv tool dir --bin``, ``uv cache dir``, ``uv python dir``
    - - PEP 723 inline script
      - ``pipx run script.py`` (with uv backend uses ``uv run``)
      - ``uv run --script script.py``

Only in pipx
============

-  ``pipx inject`` / ``uninject`` add or remove a package in place. ``uv tool install --with`` reaches the same end
   state by rebuilding the venv.
-  ``pipx runpip <venv> -- ...`` runs pip inside a tool's venv. uv venvs have no pip.
-  ``--include-deps`` exposes entry points from every dependency. uv requires you to enumerate dep packages with
   ``--with-executables-from``.
-  ``--suffix`` keeps two copies of the same tool side-by-side.
-  ``--global`` and the ``PIPX_GLOBAL_*`` variables drive a system-wide install.
-  Manual pages get symlinked under ``$PIPX_MAN_DIR``.
-  ``pipx manifest sync <manifest>`` applies an explicit desired set; ``pipx manifest lock <manifest>`` writes one PEP
   751 lock per selected tool.
-  ``pipx install-all <spec.json>`` rebuilds every venv from a ``pipx list --output json`` snapshot for cross-machine
   migration.
-  ``[project.entry-points."pipx.run"]`` declares pipx-specific runtime extras in the package metadata.
-  ``pipx environment`` prints every variable and its resolved value in one place.
-  ``--cooldown DAYS`` provides the same release-age policy through pip and uv.

Only in uv tool
===============

-  ``uv tool list`` toggles columns via ``--show-with``, ``--show-paths``, ``--show-version-specifiers``,
   ``--show-extras``, ``--show-python``.
-  ``uvx --with-editable PATH`` adds editable extras for a one-off run.
-  ``uv tool upgrade --all -p 3.13`` re-pins every tool to a different Python in one shot.
-  ``uv python install/list/find/pin/upgrade/uninstall`` integrates managed Python; uv auto-fetches when the requested
   Python isn't installed.
-  ``--torch-backend`` and ``--isolated`` add controls that pipx does not expose.
-  The content-addressed cache spans ``uv pip``, ``uv tool``, ``uv run``, and ``uv venv``. Wheels downloaded once get
   reused everywhere.

Gotchas
=======

-  ``uvx`` reuses cached envs across invocations until you prune the cache (``uv cache clean``), pin a new version
   (``uvx black@latest``), or pass ``--refresh``. ``pipx run`` caches for 14 days and accepts ``--refresh`` for an early
   replacement.
-  ``uvx`` prefers a persistent install when one exists. After ``uv tool install ruff``, plain ``uvx ruff`` reuses that
   env instead of building an ephemeral one. Pass ``--isolated`` to bypass.
-  ``uv tool`` ignores project-local ``.python-version`` files. ``uv run`` honors them; tool envs do not. pipx never
   reads them; pass ``--python`` or set ``PIPX_DEFAULT_PYTHON``.
-  ``uv python upgrade`` only bumps patch versions. To move a tool from 3.12 to 3.13 run ``uv tool upgrade --all -p
   3.13``. pipx's equivalent is ``reinstall-all --python python3.13``.
-  ``uv run --script`` needs a real on-disk path. When ``pipx run script.py`` content arrives via URL or named pipe, the
   uv backend falls back to building a venv.

Picking one
===========

pipx wins when you need its tool-specific extras: ``inject``/``uninject``, ``--global``, ``--suffix``, manual pages, or
``pipx install-all`` for migration. Install ``pipx[uv]`` to keep that surface and pick up uv-speed venv creation. Reach
for ``uv tool`` when you already drive uv for managed Python or ``uv run --script`` and want one binary for everything.
Running both is fine; the only collision point is the shared bin dir, and both sides refuse to overwrite without
``--force``.

**************************
 pipx vs poetry and pipenv
**************************

-  pipx is used solely for application consumption: you install CLI apps with it.
-  pipenv and poetry are CLI apps used to develop applications and libraries.
-  All three tools wrap pip and virtual environments for more convenient workflows.

Example: install poetry with pipx, ``pipx install poetry``; run poetry without installing it, ``pipx run poetry
--help``.

**************
 pipx vs venv
**************

-  venv is part of Python's standard library in Python 3.2 and above.
-  venv creates "virtual environments", which are sandboxed Python installations.
-  pipx relies heavily on the venv package.

Example: pipx installs packages into environments created with venv, ``pipx install black --verbose``.

***************
 pipx vs pyenv
***************

-  pyenv manages Python versions on your system. It helps you install versions like Python 3.11, 3.12, and so on.
-  pipx installs packages in virtual environments and exposes their entry points on your ``PATH``.

Example: install a Python interpreter with pyenv, then install a package with pipx using that interpreter, ``pipx
install black --python=python3.11`` where ``python3.11`` was installed by pyenv.

***************
 pipx vs pipsi
***************

-  pipx and pipsi both install packages in a similar way.
-  pipx is under active development; pipsi is no longer maintained.
-  pipx always makes sure you're using the latest version of pip.
-  pipx can run an app in one line, leaving your system unchanged after it finishes (``pipx run APP``); pipsi cannot.
-  pipx can recursively install binaries from dependent packages.
-  pipx has more CLI options such as ``upgrade-all``, ``reinstall-all``, and ``uninstall-all``.
-  pipx is more modern. It requires Python 3.10+ and uses the standard-library ``venv`` package.
-  pipx works with Python homebrew installations while pipsi does not.
-  pipx lets you see each command it runs by passing ``--verbose``.

Migrating to pipx from pipsi
============================

After you have installed pipx, run `migrate_pipsi_to_pipx.py
<https://raw.githubusercontent.com/pypa/pipx/main/scripts/migrate_pipsi_to_pipx.py>`_. You can do this with pipx itself:

.. code-block:: console

    $ pipx run https://raw.githubusercontent.com/pypa/pipx/main/scripts/migrate_pipsi_to_pipx.py

**************
 pipx vs brew
**************

-  Both brew and pipx install CLI tools.
-  They install from different sources: brew uses a curated repository specific to brew, and pipx generally uses PyPI.

Example: brew can install pipx, but the two generally do not interact much.

*************
 pipx vs npx
*************

-  Both can run CLI tools. npx searches ``node_modules`` and otherwise runs in a temporary environment; ``pipx run``
   searches ``__pypackages__`` and otherwise runs in a temporary environment.
-  npx works with JavaScript and pipx works with Python.
-  Both make running executables written in a dynamic language as easy as possible.
-  pipx can also install tools globally; npx cannot.

Example: none. These tools work for different languages.

*****************
 pipx vs pip-run
*****************

`pip-run <https://github.com/jaraco/pip-run>`_ is focused on running **arbitrary Python code in ephemeral environments**,
while pipx is focused on running **Python binaries in ephemeral and non-ephemeral environments**.

For example, these two commands both install poetry to an ephemeral environment and invoke poetry with ``--help``:

.. code-block:: bash

    pipx run poetry --help
    pip-run poetry -- -m poetry --help

***************
 pipx vs fades
***************

`fades <https://github.com/PyAr/fades>`_ runs **individual** Python scripts inside automatically provisioned virtualenvs
with their dependencies installed.

-  Both `fades <https://github.com/PyAr/fades#how-to-mark-the-dependencies-to-be-installed>`_ and :doc:`pipx run
   <../reference/examples>` let you specify a script's dependencies in specially formatted comments, but the exact syntax
   differs. pipx's syntax is standardized by a `provisional specification
   <https://packaging.python.org/en/latest/specifications/inline-script-metadata/>`_; fades's syntax is not.
-  Both tools automatically set up reusable virtualenvs containing the necessary dependencies.
-  Both can download Python scripts or packages to execute from remote resources.
-  fades can only run individual script files while pipx can also run packages.

***********************
 pipx vs pae/pactivate
***********************

*pae* is a Bash command-line function distributed with `pactivate <https://github.com/cynic-net/pactivate>`_ that uses
pactivate to create non-ephemeral environments focused on general use, rather than just running command-line
applications.

There is a `detailed comparison <https://github.com/cynic-net/pactivate/blob/main/doc/vs-pipx.md>`_, but to summarize:

Similarities:

-  Both create isolated environments without having to specify (and remember) a directory in which to store them.
-  Both let you use any Python interpreter available on your system (subject to the version restrictions below).

pae advantages:

-  Supports all versions of Python from 2.7 upward. pipx requires 3.10 or above.
-  Fewer dependencies.
-  Easier to have multiple versions of a single program, or use different Python versions for one program.
-  Somewhat more convenient for running arbitrary command-line programs in virtual environments, installing multiple
   packages in a single environment, and activating virtual environments.
-  Integrates well with source repos using `pactivate <https://github.com/cynic-net/pactivate>`_.

pae disadvantages:

-  Usable with the Bash shell only.
-  Slightly less quick and convenient for installing or running command-line programs from single Python packages.
-  Can be slower than pipx at creating virtual environments.
