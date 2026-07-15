############
 Expose apps
############

Control which apps and manual pages an environment links onto your ``PATH``, without rebuilding it.

************
 Hide an app
************

Use ``unexpose`` when another command with the same name should win, but you want to keep the environment:

.. code-block:: console

    $ pipx unexpose ansible

pipx removes the apps and manual pages recorded for that environment from its global directories. Upgrade and reinstall
keep it hidden, and injected apps stay hidden too.

***************
 Restore an app
***************

.. code-block:: console

    $ pipx expose ansible

pipx relinks each recorded app and manual page without rebuilding the environment.

***************************
 Expose a dependency's apps
***************************

A dependency's apps are not exposed by default. Select them at install time.

``--include-deps`` exposes apps and manual pages from every dependency:

.. code-block:: console

    $ pipx install nox --include-deps

``--include-resources-from PACKAGE`` exposes resources from one dependency; repeat it to select more:

.. code-block:: console

    $ pipx install "nox[tox_to_nox]" --include-resources-from tox

pipx records the selection so upgrade and reinstall preserve it. The install fails and rolls back when a selected
package is not a dependency that ships apps or manual pages. Both options also work on ``pipx inject``; see
:doc:`inject-packages`.

.. note::

    ``--include-apps-from`` was renamed to ``--include-resources-from``. pipx still reads the old name from metadata
    written by earlier versions.

**********
 Verify it
**********

.. code-block:: console

    $ pipx list

The exposed apps appear under their environment. Run one to confirm it resolves on your ``PATH``.
