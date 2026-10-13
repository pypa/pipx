#############
 Pin packages
#############

Hold an installation at its current version so upgrades skip it until you unpin.

*******
 Pin it
*******

.. code-block:: console

    $ pipx pin black

Pinned environments are skipped by ``pipx upgrade`` and ``pipx upgrade-all``, so the app and its dependencies keep their
versions until you unpin. ``pipx reinstall`` refuses a pinned environment, and ``pipx reinstall-all`` reports it as an
error. ``pipx install --force`` and ``pipx inject --force`` keep a package pinned, even when they install a different
version.

- ``pipx pin PACKAGE`` pins the main package and any injected packages in that environment.
- ``pipx pin PACKAGE --injected-only`` leaves the main package upgradable but pins every injected package.
- ``pipx pin PACKAGE --skip PKG_A PKG_B`` pins injected packages except the listed ones (implies ``--injected-only``).
- ``pipx unpin PACKAGE`` unpins the main package and every pinned injected package in that environment.

Pass ``--output json`` to read the changed and skipped packages from a script, or ``--quiet`` to omit confirmations.

.. note::

    pipx pins the main package and injected packages, not individual transitive dependencies. Pinning the main package
    freezes its whole dependency set, because pipx skips ``pip install --upgrade`` for that environment. A package
    injected after ``pipx pin`` starts unpinned, so ``pipx upgrade --include-injected`` still upgrades it; run ``pipx
    pin PACKAGE`` again to pin it too. For how pipx records this metadata, see :doc:`../explanation/how-pipx-works`.

**********
 Verify it
**********

.. code-block:: console

    $ pipx list --pinned

Add ``--include-injected`` to also list pinned injected packages.
