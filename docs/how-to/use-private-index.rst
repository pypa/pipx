####################
 Use a private index
####################

Install from a private index, behind a proxy, or offline by forwarding index options to the backend.

******************************
 Set the index for one command
******************************

Pass ``--index-url`` directly, or forward pip options with ``--pip-args``:

.. code-block:: console

    $ pipx install my-package --index-url https://my-index.example.com/simple/
    $ pipx install my-package --pip-args="--extra-index-url https://my-index.example.com/simple/"

Quote ``--pip-args`` and use an ``=`` sign so pipx passes the whole string through. Add trusted hosts and other pip
flags the same way:

.. code-block:: console

    $ pipx install my-package --pip-args="--index-url https://my-index.example.com/simple/ --trusted-host my-index.example.com"

*************************
 Set it for every command
*************************

pipx forwards ``PIP_*`` environment variables to every pip invocation, including shared-library upgrades. Set them in
your shell profile or pip's own config file for a permanent default:

.. code-block:: console

    $ export PIP_INDEX_URL=https://my-index.example.com/simple/
    $ export PIP_TRUSTED_HOST=my-index.example.com
    $ pipx install my-private-package

See the `pip configuration docs <https://pip.pypa.io/en/stable/topics/configuration/>`_ for the config-file form.

****************
 Install offline
****************

Point pip at a local directory of wheels and stop it reaching the network:

.. code-block:: console

    $ pipx install my-package --pip-args="--no-index --find-links /path/to/wheels"

Pass ``--skip-maintenance`` to keep the bundled pip instead of downloading a shared-library upgrade during the install.

.. warning::

    Under the uv backend, pipx translates only a small subset of ``--pip-args``: ``--index-url``, ``--extra-index-url``,
    ``--find-links``, and ``--pre``. Any other flag raises an error rather than being silently dropped. Use
    ``--backend pip`` when you need a flag uv cannot translate. See :doc:`use-uv-backend`.

**********
 Verify it
**********

.. code-block:: console

    $ pipx list --short

The package installs at the version your index serves. For a private index that pipx must also use for its own shared
libraries, set the ``PIP_*`` variables before the first install.
