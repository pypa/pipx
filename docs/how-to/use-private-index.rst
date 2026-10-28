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

pipx records these options and passes them again on ``pipx upgrade`` and ``pipx reinstall``. A ``pipx runpip <venv>
install`` that reinstalls the main package with index options (``--index-url``, ``--extra-index-url``, ``--find-links``,
``--trusted-host``, ``--no-index``, or uv's ``--default-index``, ``--index``, ``--index-strategy``,
``--allow-insecure-host``, ``--keyring-provider``) replaces the recorded ones with them; without index options the
record stays.

*************************
 Set it for every command
*************************

Under the pip backend, pipx forwards ``PIP_*`` environment variables to every pip invocation, including shared-library
upgrades. Set them in your shell profile or pip's own config file for a permanent default:

.. code-block:: console

    $ export PIP_INDEX_URL=https://my-index.example.com/simple/
    $ export PIP_TRUSTED_HOST=my-index.example.com
    $ pipx install my-private-package

See the `pip configuration docs <https://pip.pypa.io/en/stable/topics/configuration/>`_ for the config-file form. pipx
always sets ``PIP_USER=0`` and drops ``PIP_TARGET`` so packages land in the venv. The uv backend ignores ``PIP_*``; use
uv's own variables (for example ``UV_INDEX_URL``) or ``--backend pip``.

****************
 Install offline
****************

Point pip at a local directory of wheels and stop it reaching the network:

.. code-block:: console

    $ pipx install my-package --pip-args="--no-index --find-links /path/to/wheels"

Pass ``--skip-maintenance`` to keep the bundled pip instead of downloading a shared-library upgrade during the install.

.. warning::

    Under the uv backend, ``pipx run`` translates only a subset of ``--pip-args``: ``--index-url`` (``-i``),
    ``--extra-index-url``, ``--find-links`` (``-f``), ``--trusted-host``, ``--no-binary``, ``--only-binary``,
    ``--pre``, ``--upgrade`` (``-U``), and ``--no-cache-dir``. Any other flag raises an error rather than being
    silently dropped. Other commands pass ``--pip-args`` to ``uv pip install`` unchanged, so uv decides which flags it
    accepts. Use ``--backend pip`` when you need a pip-only flag. See :doc:`use-uv-backend`.

**********
 Verify it
**********

.. code-block:: console

    $ pipx list --short

The package installs at the version your index serves. For a private index that pipx must also use for its own shared
libraries, set the ``PIP_*`` variables before the first install.
