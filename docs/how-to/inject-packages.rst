################
 Inject packages
################

Add extra packages into an existing pipx-managed environment with ``pipx inject``.

*****************
 Inject a package
*****************

Add ``matplotlib`` to the ``ipython`` environment:

.. code-block:: console

    $ pipx inject ipython matplotlib

Inject several at once, from a requirements file, or both:

.. code-block:: console

    $ pipx inject ipython matplotlib pandas
    $ pipx inject ipython -r useful-packages.txt
    $ pipx inject ipython extra-pkg -r more-packages.txt

Scripts can request the versioned result envelope from either command:

.. code-block:: console

    $ pipx inject ipython matplotlib --output json
    $ pipx uninject ipython matplotlib --output json

*********************
 Expose injected apps
*********************

Injected packages do not add their entry points to your ``PATH`` by default. Use ``--include-apps`` to expose them:

.. code-block:: console

    $ pipx inject ipython black --include-apps

``--include-deps`` exposes apps and manual pages from every dependency. Use ``--include-resources-from PACKAGE`` to
expose one dependency, repeating it to select more. Both options imply ``--include-apps``.

.. code-block:: console

    $ pipx inject robotframework-keyta robotframework-browser-batteries --include-resources-from robotframework-browser

For exposing apps from an already-installed environment, see :doc:`expose-apps`.

************
 Other flags
************

- ``--force`` / ``-f`` reinstalls the package even when it is already injected.
- ``--editable`` / ``-e`` installs the package in editable (development) mode.
- ``--with-suffix`` targets a suffixed venv (for example ``ipython_3.11``).
- ``--pip-args`` passes extra arguments to pip (for example ``--pip-args='--no-cache-dir'``).
- ``--index-url`` / ``-i`` sets the package index URL for this inject.
- ``--system-site-packages`` gives the venv access to the system site-packages.

**********
 Verify it
**********

.. code-block:: console

    $ pipx list --include-injected

The injected packages appear under their host environment.
