#############
 Contributing
#############

Thanks for your interest in contributing to pipx!

We expect everyone who interacts with the pipx project via codebase, issue tracker, chat rooms, or otherwise to follow
the `PSF Code of Conduct <https://github.com/pypa/.github/blob/main/CODE_OF_CONDUCT.md>`_.

*******************
 Submitting changes
*******************

#. Fork `the GitHub repository <https://github.com/pypa/pipx>`_.
#. Make a branch off ``main`` and commit your changes to it.
#. Add a user-facing changelog entry, or apply ``skip news`` to a maintenance-only pull request.
#. Submit a pull request to the ``main`` branch on ``GitHub``, referencing an open issue.

Changelog entries
=================

`towncrier <https://pypi.org/project/towncrier/>`_ builds the changelog from news fragments in ``changelog.d/``. Name a
fragment ``+topic.type.rst`` before opening a pull request, for example ``+reset-eof.bugfix.rst``. Existing numbered
names such as ``1234.bugfix.rst`` remain valid. The release workflow gets the pull request number, the commit author,
and its co-authors from the squash commit and links them when it assembles the changelog.

Use ``feature`` for new capabilities and Python support additions or removals; either causes a minor version bump.
Use ``change`` for user-visible behavior changes, ``bugfix`` for corrections, ``doc`` for documentation, ``security``
for security fixes, and ``performance`` for speed or resource improvements. ``deprecation`` announces a future removal;
``removal`` describes a removed command or option; ``packaging`` covers user-visible distribution or installation
changes. Use ``breaking`` only for an incompatible behavior change that is not a Python support change.

One pull request may carry several fragments, including two of the same type: ``+reset-eof.bugfix.rst`` and
``+reset-output.bugfix.rst`` are separate entries. Write each one as a concrete sentence about the effect for a pipx
user. Internal tests, dependency updates, and CI work need no entry; apply ``skip news`` instead. Bot pull requests
without a fragment receive that label automatically. If a bot supplies a fragment, the changelog check validates it.

Do not put a pull request link or author credit in the fragment; hand-written credits fail the changelog check. The
release workflow appends the squash pull request link and credits the commit's human author and co-authors in the RST
changelog. GitHub Release notes use their handles. Keep each fragment wrapped to 120 columns; `prek
<https://github.com/j178/prek>`_ formats the generated changelog before the release commit.

**********
 Concepts
**********

pipx manages one **environment** per installed application: a virtual environment under ``PIPX_HOME`` named after its
**main package**, plus an optional suffix. ``pipx inject`` adds **injected packages** to an existing environment. pipx
resolves ``PIPX_HOME`` and every other location from environment variables, platform defaults, and legacy fallback
paths (see :doc:`reference/environment-variables`).

A **backend** installs packages into environments. The pip backend links every environment to one **shared pip**
environment through a ``.pth`` file; the uv backend calls ``uv venv`` and ``uv pip`` and needs no shared environment.
Each environment runs on an **interpreter** that pipx resolves from ``--python``. When ``--fetch-python`` is
``missing`` or ``always``, pipx downloads a standalone build from `python-build-standalone
<https://github.com/astral-sh/python-build-standalone/releases>`_ and caches it; ``pipx interpreter list``, ``prune``,
and ``upgrade`` manage those builds.

After an install, pipx **exposes** the package's resources: its console and GUI scripts (**apps**), man pages, and shell
completions, linked into ``PIPX_BIN_DIR``, ``PIPX_MAN_DIR``, and ``PIPX_COMPLETION_DIR``. Each environment's
**metadata** records the install source, backend, pip arguments, interpreter, and exposed resources, so ``upgrade``,
``reinstall``, and ``install-all`` can rebuild the same state.

``pipx run`` uses the **run cache** instead: temporary environments keyed on the requirements and installer settings,
which expire after 14 days. A **script** with :pep:`723` inline metadata works as a package: ``pipx run`` installs its
declared dependencies into a cached temporary environment, and ``pipx install`` hands either backend the same wheel
built from the script and records its path or URL.

**Example: installing black.** ``pipx install black`` resolves the default interpreter, creates the ``black``
environment, and has the backend install ``black`` into it. pipx then exposes the ``black`` and ``blackd`` apps and
records the source ``black`` and its pip arguments in the metadata. A later ``pipx upgrade black`` reads that metadata,
upgrades the package with the same backend and arguments, exposes any apps the new version adds, and removes the links
of any it dropped.

*****************************
 Running pipx For Development
*****************************

To develop ``pipx``, either create a :ref:`developer environment <creating-a-developer-environment>`, or perform an
editable install:

.. code-block:: console

    $ python -m pip install -e .
    $ python -m pipx --version

**************
 Running Tests
**************

Setup
=====

pipx uses `tox <https://pypi.org/project/tox/>`_ for development, continuous integration testing, and other tasks.
``tox list`` shows its environments; at the time of writing, the output looks like this:

.. code-block:: text

    default environments:
    3.15 -> run tests with 3.15
    3.14 -> run tests with 3.14
    3.13 -> run tests with 3.13
    3.12 -> run tests with 3.12
    3.11 -> run tests with 3.11
    3.15t -> run tests with 3.15t
    docs -> build documentation
    lint -> run pre-commit on the codebase
    man  -> build man page
    type -> run the type checker

    additional environments:
    dev       -> generate a DEV environment
    docs-live -> serve documentation with live reload
    zipapp    -> build zipapp via shiv

.. _creating-a-developer-environment:

Creating a developer environment
================================

For development (and to attach your IDE), create a Python environment with ``tox run -e dev``, then use the interpreter
at ``.tox/dev/bin/python``.

Unit Tests
==========

Run the unit tests on Python 3.15 with:

.. code-block:: console

    $ tox run -e 3.15

.. tip::

    ``tox`` passes the arguments after ``--`` to `pytest <https://docs.pytest.org>`_, the test runner pipx uses, so
    ``-k EXPRESSION`` selects tests by name:

    .. code-block:: console

        $ tox run -e 3.15 -- -k test_uninstall

    You can usually ignore coverage errors when you run only a subset of tests.

Running Unit Tests Offline
==========================

The unit tests need a ``.pipx_tests/package_cache`` directory populated from a fixed list of package distribution files
(wheels or source files). With network access, ``tox`` populates it as a first step, downloading files when needed, so
you can skip the rest of this section.

To run the tests without network access, populate ``.pipx_tests/package_cache`` beforehand, while you still have
network access.

Lint Tests
==========

Linting runs through `pre-commit <https://pre-commit.com/>`_, wired into the ``lint`` tox environment:

.. code-block:: console

    $ tox run -e lint

The main hooks are ``ruff-check`` and ``ruff-format`` (lint and format Python), ``codespell`` (spelling), ``mdformat``
(Markdown, wrapped at 120), ``yamlfmt`` (YAML), ``pyproject-fmt`` (``pyproject.toml``), and ``flake8-lazy``.

``flake8-lazy`` keeps the ``__lazy_modules__`` list at the top of each pipx module up to date. On Python 3.15 and later
(:pep:`810`) the modules it lists load on first use rather than at import, which shortens CLI startup; older Pythons
ignore the list. The hook rewrites the list itself, so when it fails, review and stage its change. A module whose import
has a side effect that must happen at startup (reading environment variables or terminal state) belongs in
``standalone.lazy-exclude-modules`` under ``[tool.flake8-lazy]`` in ``pyproject.toml``.

Type checking
=============

Type checking uses `ty <https://github.com/astral-sh/ty>`_ and runs in its own tox environment rather than
``pre-commit``, since pre-commit.ci cannot install its heavier dependency set:

.. code-block:: console

    $ tox run -e type

A dedicated `GitHub Actions <https://docs.github.com/actions>`_ job runs the same check on every pull request.

Installing or injecting new packages in tests
=============================================

When a test installs or injects a package and version that no other test uses, add it to the package lists in
``testdata/tests_packages``:

#. Add the package to ``testdata/tests_packages/primary_packages.txt``.
#. Run the *Create tests package lists for offline tests* workflow from the ``GitHub Actions`` tab, which generates the
   lists for every platform.
#. Download each ``lists-<os>-<python>`` artifact and put its files into ``testdata/tests_packages/``.
#. Commit the new or modified list files in ``testdata/tests_packages``.

**********************************************
 Testing pipx on Continuous Integration builds
**********************************************

``GitHub Actions`` runs the checks when you open a pull request.

***********************
 Building Documentation
***********************

`Sphinx <https://www.sphinx-doc.org>`_ builds the documentation from the ``docs`` directory; edit the pages there. Build
the HTML documentation with:

.. code-block:: console

    $ tox run -e docs

This runs ``sphinx-build`` with ``-W --keep-going``, so any warning fails the build. `sphinx-argparse-cli
<https://github.com/tox-dev/sphinx-argparse-cli>`_ generates the CLI reference from pipx's argument parser, so it cannot
drift from the commands. For a live-reloading preview while editing, use ``tox run -e docs-live``.

********************************
 Releasing New ``pipx`` Versions
********************************

The protected pre-release workflow determines the next version from the fragment types, builds the changelog, runs
``release-creator contributors`` to add a *New Contributors* subsection, formats the changelog with ``prek``, and
prepares a patch. The repository-scoped App then pushes the release commit and annotated tag.

Initiating a Release
====================

Run **Pre-release** from the Actions tab on ``main``. Choose ``auto`` to calculate the version from the fragments, or
choose ``major``, ``minor``, or ``patch`` to override the bump. The input is a bump type, never a typed version number.
To preview the same inputs locally without pushing, run ``python scripts/release.py`` or ``python scripts/release.py
--bump minor`` from an installed ``release`` dependency group.

What Happens During Release
===========================

The tag starts the release workflow. It builds the sdist and wheel with locked build dependencies, and builds
``pipx.pyz`` from the wheel and the runtime dependencies locked for the zipapp targets. In parallel it renders Markdown
notes from that tag's RST changelog. Once the zipapp passes its smoke test, the distributions go to `PyPI
<https://pypi.org>`_ with `trusted publishing <https://docs.pypi.org/trusted-publishers/>`_. After ``PyPI`` has the
expected files, a single step creates the GitHub Release with the zipapp attached.

Retry a failed run with "Re-run failed jobs", which uploads the same built files; the release job checks their SHA256
digests against ``PyPI`` before it writes the GitHub Release.

Version Calculation Examples
============================

Starting from ``1.8.0``, ``auto`` with a feature becomes ``1.9.0`` and ``auto`` with only bug fixes becomes ``1.8.1``.
Selecting ``major`` yields ``2.0.0``, ``minor`` yields ``1.9.0``, and ``patch`` yields ``1.8.1``. Removing support for
an older Python is a feature here because earlier pipx releases remain installable on that interpreter.
