############
 Run scripts
############

Run an app or a script in a temporary environment with ``pipx run``, without installing it first. pipx downloads the
package, caches the environment, and runs the app.

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

``--with PKG`` adds packages to the temporary environment alongside the app. Repeat it to add more:

.. code-block:: console

    $ pipx run --with requests --with rich my-script.py

*************************
 Pass arguments to Python
*************************

``--python-args ARGS`` forwards arguments to the interpreter that runs the app, rather than to the app itself:

.. code-block:: console

    $ pipx run --python-args "-X dev" my-script.py

************************
 Run from source control
************************

``pipx run`` accepts source-control URLs directly, with the same syntax as ``pipx install`` (see
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

You can run ``.py`` files hosted anywhere:

.. code-block:: console

    $ pipx run https://gist.githubusercontent.com/cs01/fa721a17a326e551ede048c5088f9e0f/raw/6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py

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

pipx caches an environment keyed to the script's dependency list. Changing the dependencies builds a fresh one.

**********
 Verify it
**********

.. code-block:: console

    $ pipx run pycowsay moo

A successful run prints the app's own output; nothing is left installed afterward.
