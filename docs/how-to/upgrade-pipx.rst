#############
 Upgrade pipx
#############

Move pipx itself to the latest release. Pick the method that matches how you installed it.

***************
 Upgrade per OS
***************

macOS:

.. code-block:: console

    $ brew update && brew upgrade pipx

Ubuntu Linux:

.. code-block:: console

    $ sudo apt update && sudo apt upgrade pipx

Fedora Linux:

.. code-block:: console

    $ sudo dnf upgrade pipx

Windows (Scoop):

.. code-block:: console

    $ scoop update pipx

**********************
 Self-managed installs
**********************

If pipx manages its own installation (see :ref:`install-from-source-control` and the self-managed bootstrap in
:doc:`install-pipx`), upgrade it like any other pipx app:

.. code-block:: console

    $ pipx upgrade pipx

****************
 Upgrade via pip
****************

When you installed pipx with ``pip install --user`` and cannot upgrade it as a pipx app:

.. code-block:: console

    $ python3 -m pip install --user --upgrade pipx

.. warning::

    On systems that adopt `PEP 668 <https://peps.python.org/pep-0668/>`_ (Ubuntu 23.04+, Debian 12+, Fedora 38+), this
    fails with ``externally-managed-environment``. Use the distribution package or the self-managed path above instead.
    See :doc:`install-pipx` for the PEP 668 install options.

**********
 Verify it
**********

.. code-block:: console

    $ pipx --version

.. note::

    Upgrading from a pre-0.15.0.0 pipx to 0.15.0.0 or later requires reinstalling your packages so they gain the
    persistent metadata files that release introduced. These files store the pip spec, injected packages, and custom pip
    arguments in each venv. With no ``--spec`` installs and no injected packages, run ``pipx reinstall-all``. Otherwise
    reinstall manually: ``pipx uninstall-all`` followed by ``pipx install`` and, where needed, ``pipx inject``.
