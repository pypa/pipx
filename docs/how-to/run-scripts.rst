############
 Run scripts
############

Run an app or a script in a temporary environment with ``pipx run``, without installing it first. pipx downloads the
package, caches the environment, and runs the app. Under the `uv <https://github.com/astral-sh/uv>`__ backend, pipx
hands packages to ``uv tool run`` and local scripts with inline metadata to ``uv run --script``. uv's cache applies to
packages, while a script's environment stays in pipx's cache.

***********************
 Run a specific version
***********************

The ``PACKAGE`` argument is a `requirement specifier
<https://packaging.python.org/en/latest/glossary/#term-Requirement-Specifier>`_, so you can pin versions, ranges, or
extras:

.. code-block:: console

    $ pipx run mpremote==1.20.0
    $ pipx run --spec esptool==4.6.2 esptool.py
    $ pipx run --spec 'esptool>=4.5' esptool.py

Quote any specifier that contains ``>``, ``<``, or spaces.

***********************
 Add extra dependencies
***********************

``--with PKG`` adds packages to the temporary environment alongside the app. Repeat it to add more. For a script,
``--with`` requires a ``# /// script`` metadata block; pipx adds the packages to its declared dependencies:

.. code-block:: console

    $ pipx run --with requests --with rich my-script.py

pipx resolves the ``--with`` packages together with the app, so ``--with`` can also pin or cap one of the app's own
dependencies:

.. code-block:: console

    $ pipx run --with 'click<8.2' black --version

*************************
 Pass arguments to Python
*************************

``--python-args ARGS`` forwards arguments to the interpreter that runs the app, rather than to the app itself:

.. code-block:: console

    $ pipx run --python-args "-X dev" my-script.py

************************
 Run from source control
************************

``pipx run`` accepts source-control URLs, with the same syntax as ``pipx install`` (see
:ref:`install-from-source-control`). Using ``black`` as an example:

.. code-block:: console

    $ pipx run git+https://github.com/psf/black.git
    $ pipx run git+https://github.com/psf/black.git@branch

Use ``--spec`` when the executable name differs from the package name or when installing from an archive URL:

.. code-block:: console

    $ pipx run --spec https://github.com/psf/black/archive/18.9b0.zip black

***************
 Run from a URL
***************

pipx downloads a script with Python's ``urllib``, which cannot send credentials embedded in an HTTP URL. ``pipx run``
and ``pipx install`` therefore refuse an ``http`` or ``https`` script URL with a ``user@`` or ``user:password@`` part.
Otherwise you can run ``.py`` files hosted anywhere:

.. code-block:: console

    $ pipx run https://gist.githubusercontent.com/cs01/fa721a17a326e551ede048c5088f9e0f/raw/6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py

A script read from a URL or a named pipe has no directory of its own, so pipx starts it with ``python -P``: it cannot
import modules from the directory you run ``pipx run`` in. The same holds for apps declared as ``pipx.run`` entry points
and for apps run with ``--python-args``.

.. _run-pep-723:

*****************************************
 Run a script with dependencies (PEP 723)
*****************************************

A script can declare its own dependencies with `inline script metadata
<https://packaging.python.org/en/latest/specifications/inline-script-metadata/>`_. pipx reads the ``# /// script`` block
and installs the listed packages before running:

.. code-block:: python

    # test.py

    # /// script
    # dependencies = ["requests"]
    # ///

    import sys
    import requests

    project = sys.argv[1]
    data = requests.get(f"https://pypi.org/pypi/{project}/json").json()
    print(data["info"]["version"])

.. code-block:: console

    $ pipx run test.py pipx
    1.9.0

pipx caches an environment keyed to the script's dependency list. Changing the dependencies builds a fresh one. Under
the uv backend pipx keys a local script's environment to the script's path instead, and uv syncs the dependencies into
it on each run. Under both backends a changed ``--python``, ``--pip-args`` or ``--cooldown`` also builds a fresh one,
and ``--refresh`` rebuilds it.

On Windows under the uv backend, a ``--refresh`` or ``--no-cache`` run of a script that another run is still executing
leaves that run's environment alone: it builds a throwaway one for itself, and after ``--refresh`` the next run to find
the cached environment idle rebuilds it.

When the block sets ``requires-python``, pipx keeps the default Python if it satisfies the constraint and otherwise
looks for an interpreter that does, the same way ``pipx install`` does (see :doc:`standalone-python`). An explicit
``--python`` that fails the constraint is an error. Both backends follow this rule.

**********
 Verify it
**********

.. code-block:: console

    $ pipx run pycowsay moo

A successful run prints the app's own output; nothing is left installed afterward.
