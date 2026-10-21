#############
 Contributing
#############

Thanks for your interest in contributing to pipx!

Everyone who interacts with the pipx project via codebase, issue tracker, chat rooms, or otherwise is expected to follow
the `PSF Code of Conduct <https://github.com/pypa/.github/blob/main/CODE_OF_CONDUCT.md>`_.

*******************
 Submitting changes
*******************

#. Fork `the GitHub repository <https://github.com/pypa/pipx>`_.
#. Make a branch off of ``main`` and commit your changes to it.
#. Add a user-facing changelog entry, or apply ``skip news`` to a maintenance-only pull request.
#. Submit a pull request to the ``main`` branch on GitHub, referencing an open issue.

Changelog entries
=================

The changelog at ``docs/changelog.rst`` is built by `towncrier <https://pypi.org/project/towncrier/>`_ from news
fragments in ``changelog.d/``. Name a fragment ``+topic.type.rst`` before opening a pull request, for example
``+reset-eof.bugfix.rst``. Existing numbered names such as ``1234.bugfix.rst`` remain valid. The release workflow gets
the pull request number and human authors from the squash commit and links them when it assembles the changelog.

Use ``feature`` for new capabilities and Python support additions or removals; either causes a minor version bump.
Use ``change`` for user-visible behavior changes, ``bugfix`` for corrections, ``doc`` for documentation, ``security``
for security fixes, and ``performance`` for speed or resource improvements. ``deprecation`` announces a future removal;
``removal`` describes a removed command or option; ``packaging`` covers user-visible distribution or installation
changes. Use ``breaking`` only for an incompatible behavior change that is not a Python support change.

One pull request may carry several fragments, including two of the same type: ``+reset-eof.bugfix.rst`` and
``+reset-output.bugfix.rst`` are separate entries. Write each one as a concrete sentence about the effect for a pipx
user. Internal tests, dependency updates, and CI work need no entry; apply ``skip news`` instead. Bot pull requests
without a fragment receive that label automatically. If a bot supplies a fragment, the changelog check validates it.

Do not put a pull request link or author credit in the fragment. The release workflow appends the squash pull request
link and credits its human authors in the RST changelog. GitHub Release notes use their GitHub handles. Keep each
fragment wrapped to 120 columns; the generated changelog is formatted through ``prek`` before the release commit.

**********************
 Codebase Architecture
**********************

All source code lives under ``src/pipx/``. The CLI entry point is ``main.py``, which dispatches to command modules in
``commands/``.

.. mermaid::

    flowchart TD
        MAIN["main.py<br/>CLI parser + dispatch"] --> CMDS["commands/"]
        CMDS --> INSTALL["install.py"]
        CMDS --> RUN["run.py"]
        CMDS --> UPGRADE["upgrade.py"]
        CMDS --> INJECT["inject.py"]
        CMDS --> LIST["list_packages.py"]
        CMDS --> PIN["pin.py"]
        CMDS --> INTERP_CMD["interpreter.py"]
        CMDS --> OTHER["uninstall, uninject,<br/>reinstall, ensure_path,<br/>environment, run_pip"]

        MAIN --> VENV["venv.py<br/>Venv + VenvContainer"]
        MAIN --> PATHS["paths.py<br/>PIPX_HOME resolution"]
        VENV --> SHARED["shared_libs.py<br/>shared pip venv"]
        VENV --> INSPECT["venv_inspect.py<br/>metadata reader"]
        VENV --> META["pipx_metadata_file.py<br/>JSON persistence"]

        RUN --> SPEC["package_specifier.py<br/>PEP 508 parsing"]
        RUN --> INTERP["interpreter.py<br/>Python resolution"]
        INTERP --> STANDALONE["standalone_python.py<br/>download builds"]

        style MAIN fill:#3f72af,color:#fff
        style CMDS fill:#2a9d8f,color:#fff
        style INSTALL fill:#2a9d8f,color:#fff
        style RUN fill:#2a9d8f,color:#fff
        style UPGRADE fill:#2a9d8f,color:#fff
        style INJECT fill:#2a9d8f,color:#fff
        style LIST fill:#2a9d8f,color:#fff
        style PIN fill:#2a9d8f,color:#fff
        style INTERP_CMD fill:#2a9d8f,color:#fff
        style OTHER fill:#2a9d8f,color:#fff
        style VENV fill:#7c4dff,color:#fff
        style PATHS fill:#c78c20,color:#fff
        style SHARED fill:#c78c20,color:#fff
        style INSPECT fill:#7c4dff,color:#fff
        style META fill:#7c4dff,color:#fff
        style SPEC fill:#388e3c,color:#fff
        style INTERP fill:#388e3c,color:#fff
        style STANDALONE fill:#388e3c,color:#fff

Key modules
===========

``venv.py`` is the core abstraction. ``Venv`` wraps a single virtual environment (create, install, uninstall, upgrade)
and ``VenvContainer`` manages the collection under ``PIPX_HOME/venvs/``. Both delegate pip operations to the shared
libraries venv managed by ``shared_libs.py``.

``paths.py`` resolves all directory locations from environment variables, platform defaults, and legacy fallback paths.
``pipx_metadata_file.py`` serializes install options (spec, pip args, injected packages) to JSON inside each venv so
that ``upgrade`` and ``reinstall`` can reproduce the original install.

``interpreter.py`` and ``standalone_python.py`` handle Python version resolution. When ``--fetch-python`` is ``missing``
or ``always``, pipx downloads a standalone build from `python-build-standalone
<https://github.com/astral-sh/python-build-standalone/releases>`_ and caches it locally. The ``pipx interpreter``
subcommands (list, prune, upgrade) manage these cached interpreters.

``script.py`` parses PEP 723 inline metadata. ``run`` installs the declared dependencies in a cached temporary venv.
``install`` sends both backends the same generated wheel and records the source path or URL.

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

pipx uses `tox <https://pypi.org/project/tox/>`_ for development, continuous integration testing, and various tasks.

``tox`` defines environments in ``tox.toml`` which can be run with ``tox run -e ENV_NAME``. Environment names can be
listed with ``tox list``.

Install tox for pipx development:

.. code-block:: console

    $ python -m pip install --user tox

Tests are defined as ``tox`` environments. You can see all tox environments with

.. code-block:: console

    $ tox list

At the time of this writing, the output looks like this

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

For developing the tool (and to attach to your IDE) we recommend creating a Python environment via ``tox run -e dev``,
afterwards use the Python interpreter available under ``.tox/dev/bin/python``.

Unit Tests
==========

To run unit tests in Python 3.15, you can run

.. code-block:: console

    $ tox run -e 3.15

.. tip::

    You can run a specific unit test by passing arguments to pytest, the test runner pipx uses:

    .. code-block:: console

        $ tox run -e 3.15 -- -k EXPRESSION

    ``EXPRESSION`` can be a test name, such as

    .. code-block:: console

        $ tox run -e 3.15 -- -k test_uninstall

    Coverage errors can usually be ignored when only running a subset of tests.

Running Unit Tests Offline
==========================

Running the unit tests requires a directory ``.pipx_tests/package_cache`` to be populated from a fixed list of package
distribution files (wheels or source files). If you have network access, ``tox`` automatically makes sure this
directory is populated (including downloading files if necessary) as a first step. Thus, if you are running the tests
with network access, you can ignore the rest of this section.

If, however, you wish to run tests offline without the need for network access, you can populate
``.pipx_tests/package_cache`` yourself manually beforehand when you do have network access.

Lint Tests
==========

Linting runs through `pre-commit <https://pre-commit.com/>`_, wired into the ``lint`` tox environment:

.. code-block:: console

    $ tox run -e lint

The key hooks are ``ruff-check`` and ``ruff-format`` (lint and format Python), ``codespell`` (spelling), ``mdformat``
(Markdown, wrapped at 120), ``yamlfmt`` (YAML), ``pyproject-fmt`` (``pyproject.toml``), and ``flake8-lazy``.

``flake8-lazy`` keeps the ``__lazy_modules__`` list at the top of each module under ``src/pipx`` up to date. On Python
3.15 and later (:pep:`810`) the modules it lists load on first use rather than at import, which shortens CLI startup;
older Pythons ignore the list. The hook rewrites the list itself, so when it fails, review and stage its change. A
module whose import has a side effect that must happen at startup (reading environment variables or terminal state)
belongs in ``standalone.lazy-exclude-modules`` under ``[tool.flake8-lazy]`` in ``pyproject.toml``.

Type checking
=============

Type checking uses `ty <https://github.com/astral-sh/ty>`_ and runs in its own tox environment rather than pre-commit,
since pre-commit.ci cannot install its heavier dependency set:

.. code-block:: console

    $ tox run -e type

A dedicated GitHub Actions job runs the same check on every pull request.

Installing or injecting new packages in tests
=============================================

If the tests are modified such that a new package / version combination is ``pipx install``ed or ``pipx inject``ed that
wasn't used in other tests, then one must make sure it's added properly to the packages lists in
``testdata/tests_packages``.

To accomplish this:

- Edit ``testdata/tests_packages/primary_packages.txt`` to add the new package(s) that you wish to ``pipx install`` or
  ``pipx inject`` in the tests.

Then using Github workflows to generate all platforms in the Github CI:

- Manually activate the Github workflow: Create tests package lists for offline tests
- Download each ``lists-<os>-<python>`` artifact and put the files from it into ``testdata/tests_packages/``

Finally, check-in the new or modified list files in the directory ``testdata/tests_packages``

**********************************************
 Testing pipx on Continuous Integration builds
**********************************************

Upon opening pull requests GitHub Actions will automatically trigger.

***********************
 Building Documentation
***********************

The documentation is built with Sphinx. When updating pipx docs, make sure you are modifying the ``docs`` directory.

Build the HTML documentation with

.. code-block:: console

    $ tox run -e docs

This runs ``sphinx-build`` with ``-W --keep-going``, so any warning fails the build. The CLI reference is generated
from pipx's argparse parser by sphinx-argparse-cli, so it cannot drift from the actual commands. For a live-reloading
preview while editing, use ``tox run -e docs-live``.

********************************
 Releasing New ``pipx`` Versions
********************************

The protected pre-release workflow determines the next version from the fragment types, formats the changelog with
``prek``, and prepares a patch. It validates the patch without release credentials before the repository-scoped App
pushes the release commit and annotated tag.

Initiating a Release
====================

Run **Pre-release** from the Actions tab on ``main``. Choose ``auto`` to calculate the version from the fragments, or
choose ``major``, ``minor``, or ``patch`` to override the bump. The input is a bump type, never a typed version number.
You can preview the same inputs locally without pushing by running ``python scripts/release.py`` or
``python scripts/release.py --bump minor`` from an installed ``release`` dependency group.

What Happens During Release
===========================

The tag starts the release workflow. It runs the test suite, builds and checks the sdist and wheel, renders Markdown
notes from that tag's RST changelog, and then publishes to PyPI with trusted publishing. After PyPI succeeds, a small
write-only job creates the GitHub Release from the checked notes and attaches the zipapp built by the test workflow.
The GitHub notes keep contributor credits and a comparison link without copying GitHub's generated-notes banner.

Version Calculation Examples
============================

Starting from ``1.8.0``, ``auto`` with a feature becomes ``1.9.0`` and ``auto`` with only bug fixes becomes ``1.8.1``.
Selecting ``major`` yields ``2.0.0``, ``minor`` yields ``1.9.0``, and ``patch`` yields ``1.8.1``. Removing support for
an older Python is a feature here because earlier pipx releases remain installable on that interpreter.
