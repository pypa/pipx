#############
 Pin packages
#############

Hold an installation at its current version so upgrade and reinstall skip it until you unpin.

*******
 Pin it
*******

.. code-block:: console

    $ pipx pin black

Pinned environments are skipped by ``pipx upgrade``, ``pipx upgrade-all``, and ``pipx reinstall``, so the app and its
dependencies keep their versions until you unpin.

- ``pipx pin PACKAGE`` pins the main package and any injected packages in that environment.
- ``pipx pin PACKAGE --injected-only`` leaves the main package upgradable but pins every injected package.
- ``pipx pin PACKAGE --skip PKG_A PKG_B`` pins injected packages except the listed ones (implies ``--injected-only``).
- ``pipx unpin PACKAGE`` re-enables upgrades for the package and anything pinned with it.

Pass ``--output json`` to read the changed and skipped packages from a script, or ``--quiet`` to omit confirmations.

.. note::

    pipx pins the main package and injected packages, not individual transitive dependencies. Pinning the main package
    freezes its whole dependency set, because pipx skips ``pip install --upgrade`` for that environment. For how pipx
    records this metadata, see :doc:`../explanation/how-pipx-works`.

**********
 Verify it
**********

.. code-block:: console

    $ pipx list --pinned

Add ``--include-injected`` to also list pinned injected packages.
