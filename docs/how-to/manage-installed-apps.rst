######################
 Manage installed apps
######################

List, upgrade, and remove the apps pipx manages, then confirm each change.

**********
 List apps
**********

.. code-block:: console

    $ pipx list

The output shows each package version, its apps, and the environment paths. Narrow or reshape it:

- ``pipx list --short`` prints package names and versions only.
- ``pipx list --include-injected`` also lists packages injected into each environment.
- ``pipx list --outdated`` lists environments with an available upgrade.
- ``pipx list --pinned`` lists pinned environments only.

************
 Upgrade one
************

.. code-block:: console

    $ pipx upgrade black

Add ``--include-injected`` to upgrade injected packages alongside the main app. Pass ``--install`` to install the
package spec when it is missing rather than error.

pipx exposes any apps, manual pages, and shell completions the new version adds, and removes the ones it no longer
ships, so ``pipx list`` and ``PIPX_BIN_DIR`` match the upgraded package. ``upgrade-all`` and ``pipx install --upgrade``
do the same.

Verify:

.. code-block:: console

    $ pipx list --short

************
 Upgrade all
************

.. code-block:: console

    $ pipx upgrade-all

Use ``--skip PKG ...`` to leave named environments untouched, and ``--include-injected`` to include injected packages.
Pinned environments are skipped; see :doc:`pin-packages`.

pipx upgrades up to eight environments at once and prints their output in environment order, as a one-at-a-time run
would. An app, manual page, or completion that several environments expose ends up with the same environment as in a
one-at-a-time run. A failed environment does not stop the others. Pass ``--verbose`` to upgrade them one at a time.

Verify:

.. code-block:: console

    $ pipx list --outdated

**************
 Uninstall one
**************

.. code-block:: console

    $ pipx uninstall black

pipx deletes the environment and unlinks its apps, manual pages, and shell completions.

Verify:

.. code-block:: console

    $ pipx list --short

**************
 Uninstall all
**************

.. code-block:: console

    $ pipx uninstall-all

Record what you have first with ``pipx list --short`` if you plan to reinstall later.

Verify:

.. code-block:: console

    $ pipx list

**************
 Reinstall one
**************

Rebuild an environment from its recorded metadata, keeping the same options as the original install. Reach for it after
a Python upgrade or to repair a broken environment.

.. code-block:: console

    $ pipx reinstall black

Pass ``--python`` to rebuild under another interpreter. ``pipx install --force`` keeps the environment's interpreter
and ignores ``--python``.

Verify:

.. code-block:: console

    $ pipx list --short

**************
 Reinstall all
**************

.. code-block:: console

    $ pipx reinstall-all

Common after installing a new Python version so every app moves to it. Use ``--python`` to target a specific
interpreter and ``--skip PKG ...`` to exclude environments.

pipx rebuilds up to eight environments at once (fewer on machines with fewer CPUs) and holds back the output of each
until the ones before it finish, so it reads the same as a one-at-a-time run. An app, manual page, or completion that
several environments expose ends up with the same environment as in a one-at-a-time run. A failed environment does
not stop the others. Pass ``--verbose`` to rebuild them one at a time and watch the pip or uv output as it happens.

Verify:

.. code-block:: console

    $ pipx list

.. tip::

    To check environments without changing them, or to repair only the broken ones, see :ref:`repair-environments`.
