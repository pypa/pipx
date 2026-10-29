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

Windows (`Scoop <https://scoop.sh/>`__):

.. code-block:: console

    $ scoop update pipx

**********************
 Self-managed installs
**********************

If pipx manages its own installation (see :ref:`install-from-source-control` and the self-managed bootstrap in
:doc:`install-pipx`), upgrade it like any other pipx app:

.. code-block:: console

    $ pipx upgrade pipx

A pipx installed with ``--global`` belongs to the global installation, so upgrade it there:

.. code-block:: console

    $ sudo pipx upgrade --global pipx

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

***********************************************
 Respond to a distrusted certificate authority
***********************************************

After the `eMudhra/emSign CA incident
<https://discuss.python.org/t/information-for-python-users-regarding-emudhra-emsign-ca-certificate-security-incident/109576>`_,
`pip <https://pip.pypa.io/>`__ 26.2.2 and `certifi <https://pypi.org/project/certifi/>`__ 2026.10.19 stopped trusting
the compromised root. Upgrade pipx first. Under the pip backend every app borrows the shared pip, and pipx replaces a
shared pip older than 26.2.2 the next time it installs, upgrades, reinstalls, injects or runs an app. To replace it now:

.. code-block:: console

    $ pipx upgrade-shared

Apps that depend on ``certifi`` (for example through ``requests``) carry their own copy. Upgrade it in each app that has
one:

.. code-block:: console

    $ pipx runpip APP install --upgrade "certifi>=2026.10.19"

Under the `uv <https://github.com/astral-sh/uv>`__ backend pipx runs the ``uv`` from its ``uv`` extra, or the one on your ``PATH``; upgrade that ``uv`` to
0.13.4 or later.

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
