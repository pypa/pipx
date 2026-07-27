##############
 Tool manifest
##############

Declare a set of pipx tools in one file and install, upgrade, or prune them as a unit with ``pipx manifest``.

*******************
 Write the manifest
*******************

The manifest is a ``pipx.toml`` file. Each dependency group holds one PEP 508 package requirement and names its pipx
environment. Keep ``project.dependencies`` empty so each group resolves on its own:

.. code-block:: toml

    [project]
    name = "pipx-tools"
    version = "1"
    dependencies = []
    requires-python = ">=3.10"

    [dependency-groups]
    black = ["black>=25,<26"]
    httpie = ["httpie"]

    [tool.pipx]
    version = "1.0"

    [tool.pipx.tools.black]
    apps = ["black"]
    lock = "pylock.black.toml"

    [tool.pipx.tools.httpie]
    apps = ["http", "https"]

Add a ``tool.pipx.tools`` table only when a tool needs policy beyond its package requirement. A tool table may set
``suffix``, ``apps``, ``include-dependencies``, ``include-resources-from``, ``expose``, or ``lock``. Use
``include-resources-from = ["PACKAGE"]`` to select dependency resources; do not combine it with
``include-dependencies``. Relative ``lock`` paths start from the manifest directory. Put nab settings in ``tool.nab``.

Use the normalized package name plus its suffix as the environment name when a tool sets a suffix:

.. code-block:: toml

    [dependency-groups]
    black-24 = ["black==24.10.0"]

    [tool.pipx.tools.black-24]
    suffix = "-24"
    apps = ["black"]

Package requirements use PEP 508 syntax without environment markers.

******************
 Lock the manifest
******************

`nab <https://pypi.org/project/nab/>`_ resolves each locked dependency group into a PEP 751 lock file. Install it, then
generate the declared locks:

.. code-block:: console

    $ pipx install nab
    $ pipx manifest lock ./pipx.toml

``pipx manifest lock`` passes the manifest to nab once per locked dependency group. Existing locks seed their
replacements, and pipx overwrites the declared files only after every resolution succeeds. Entries without ``lock``
stay unlocked.

*******************
 Apply the manifest
*******************

.. code-block:: console

    $ pipx manifest sync ./pipx.toml

``sync`` installs, upgrades, or downgrades each declared tool. The backend resolves unlocked specs on each run; locked
entries install from the artifacts in their named PEP 751 files. pipx restores an existing environment and its exposed
resources when a tool fails to install or lacks a required app.

Pass ``--prune`` to uninstall environments absent from the manifest:

.. code-block:: console

    $ pipx manifest sync ./pipx.toml --prune

Without ``--prune``, sync leaves your other pipx environments alone. Pass ``--global`` or ``--backend`` after ``sync``
to select the pipx store or the installation backend. pipx reads only the manifest path you supply on the command line.

**********
 Verify it
**********

.. code-block:: console

    $ pipx list --short

Each declared tool appears at the version its group resolved to.
