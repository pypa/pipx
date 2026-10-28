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
record stays. pipx resolves a relative ``--find-links`` (``-f``) path against the directory you ran ``runpip`` from and
records the absolute path, so after ``pipx runpip my-package install --no-index -f ./wheels my-package`` a later upgrade
or reinstall reads the same ``wheels`` directory from wherever you start it.

Under the uv backend, pipx passes ``--index-url`` (``-i``) to uv as ``--default-index``, so it replaces a default index
set through ``UV_DEFAULT_INDEX`` or a ``default = true`` ``[[index]]`` entry. uv still searches indexes added through
``UV_INDEX`` or other ``[[index]]`` entries before it, as it does for its own ``--default-index``.

pipx refuses an empty or whitespace-only index URL before it creates an environment, whether it comes from
``--index-url`` (``-i``) or from ``--index-url``, ``-i``, ``--extra-index-url``, ``--default-index`` or ``--index``
inside ``--pip-args``. An empty value usually means an unset variable, as in ``--index-url "$INDEX_URL"``, and uv reads
it as the default index, so the package would come from PyPI instead of your index. Under the uv backend pipx also
refuses an empty index recorded by an earlier install when ``upgrade``, ``reinstall`` or ``install-all`` replays it:

.. code-block:: console

    $ pipx install my-package --pip-args="--index-url=$UNSET_VARIABLE"
    --index-url is empty; pass the index URL or leave the option out

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
always sets ``PIP_USER=0`` and drops ``PIP_TARGET`` so packages land in the venv. For the same reason it removes pip's
site-level file, ``pip.conf`` (``pip.ini`` on Windows) in the root of the venv, before it starts pip there: installed
packages can place files in the venv root, so keep your settings in the user or global file. The uv backend ignores
``PIP_*``; use uv's own variables (for example ``UV_INDEX_URL``) or ``--backend pip``.

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
    silently dropped. Other commands pass ``--pip-args`` to ``uv pip install`` unchanged apart from ``--index-url``
    (``-i``), so uv decides which flags it accepts. Use ``--backend pip`` when you need a pip-only flag. See
    :doc:`use-uv-backend`.

**********
 Verify it
**********

.. code-block:: console

    $ pipx list --short

The package installs at the version your index serves. For a private index that pipx must also use for its own shared
libraries, set the ``PIP_*`` variables before the first install.
