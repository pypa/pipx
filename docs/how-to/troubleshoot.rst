#############
 Troubleshoot
#############

Diagnose and fix common pipx problems, from wrong package versions to broken environments.

********************************
 Wrong package version installed
********************************

pipx builds venvs with your default Python, and pip installs the newest release compatible with it. When a package
drops support for your Python version, pip installs an older release without warning.

Check which Python pipx uses:

.. code-block:: console

    $ pipx environment --value PIPX_DEFAULT_PYTHON

Install with a different Python:

.. code-block:: console

    $ pipx install my-package --python python3.12

If you do not have that version, let pipx download a standalone build:

.. code-block:: console

    $ pipx install my-package --python 3.13 --fetch-python=missing

Pass ``--fetch-python=always`` to download even when the system has the requested version, for example to avoid a
patched distro interpreter. See :doc:`standalone-python`.

.. _repair-environments:

*********************************
 Diagnose and repair environments
*********************************

Check each managed environment without changing it:

.. code-block:: console

    $ pipx health

The command exits with status 1 when an environment cannot run its Python interpreter. Pass package names to check a
subset, or ``--output json`` to read the result from a script.

Repair failed environments with the default Python:

.. code-block:: console

    $ pipx repair

Pass package names to limit the repair, and ``--python`` when the rebuilt environments need another interpreter:

.. code-block:: console

    $ pipx repair --python python3.13

``pipx repair`` reuses the recorded metadata, like ``pipx reinstall``, and leaves healthy environments unchanged. It
refuses a pinned package because its recorded source may resolve to another release; run ``pipx unpin PACKAGE`` first.
To rebuild healthy environments too (for example after an old pipx release), use ``pipx reinstall-all`` (see
:doc:`manage-installed-apps`).

.. note::

    A package installed with a pipx before 0.15.0.0 has no recorded options. To specify options, uninstall and install
    it manually:

    .. code-block:: console

        $ pipx uninstall <mypackage>
        $ pipx install <mypackage>

********************************
 Start over from a fresh install
********************************

An interrupted install or shared-library upgrade can leave state that ``pipx repair`` cannot mend, such as a shared
environment whose pip no longer imports. Reset pipx to the state it had at install time:

.. code-block:: console

    $ pipx reset

It uninstalls every managed package (unlinking their apps and man pages) and removes the shared libraries, caches,
standalone interpreters, logs, and trash. Because it asks first, ``--yes`` answers for a script, and ``--dry-run`` lists
what it would remove without touching anything:

.. code-block:: console

    $ pipx reset --dry-run

Record what you have with ``pipx list --short`` before the reset, then reinstall afterward.

**************************************
 Specify options that take an argument
**************************************

Use an ``=`` sign for options that require an argument:

.. code-block:: console

    $ pipx install pycowsay --pip-args="--no-cache-dir"

To ignore SSL/TLS errors:

.. code-block:: console

    $ pipx install termpair --pip-args '--trusted-host files.pythonhosted.org --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host github.com'

**************************************
 Check for PIP_* environment variables
**************************************

pipx uses pip to install and manage packages. If pipx behaves strangely on install or upgrade, check for environment
variables that change pip's behavior.

Unix or macOS:

.. code-block:: console

    $ env | grep '^PIP_'

Windows PowerShell:

.. code-block:: console

    $ ls env:PIP_*

Windows ``cmd``:

.. code-block:: console

    $ set PIP_

See `pip's environment variables <https://pip.pypa.io/en/stable/user_guide/#environment-variables>`_.

****************************
 Clear runpip cache warnings
****************************

``pipx runpip`` runs the pip installed inside a pipx-managed venv. Warnings such as ``WARNING: Cache entry
deserialization failed, entry ignored`` come from that pip and its own HTTP cache, not from pipx's venv cache.

Clear the cache for a managed package:

.. code-block:: console

    $ pipx runpip <package> cache purge

Inspect the cache directory first with ``--verbose`` so pipx does not quiet pip's output:

.. code-block:: console

    $ pipx runpip --verbose <package> cache dir

Clearing ``$PIPX_HOME/.cache`` or the cache for a different interpreter does not clear entries used by ``pipx runpip
<package>``.

**********
 Log files
**********

pipx writes a verbose log for every command. The last 10 logs live in ``$XDG_STATE_HOME/pipx/logs``, or the user log
path when that is not writable (usually ``~/.local/state/pipx/logs``). Set ``PIPX_MAX_LOGS`` to change how many are kept
(default ``10``).

.. _sudo-pipx-not-found:

************************
 ``sudo pipx`` not found
************************

If you installed pipx with ``pip install --user``, its binary lives in your user directory (for example
``~/.local/bin/pipx``). Root's ``PATH`` does not include that directory, so ``sudo pipx`` fails with "command not
found". Use the full path:

.. code-block:: console

    $ sudo ~/.local/bin/pipx ensurepath --global

To avoid this, install pipx through your distribution's package manager (``apt install pipx``, ``dnf install pipx``) or
system-wide with ``sudo pip install pipx`` (without ``--user``).

*************************
 Debian and Ubuntu issues
*************************

On Debian, Ubuntu, and derivatives, make sure these packages are installed; Debian systems do not add them by default:

.. code-block:: console

    $ sudo apt install python3-venv python3-pip

See the `Python Packaging User Guide
<https://packaging.python.org/guides/installing-using-linux-tools>`_ on installing pip, setuptools, and wheel with Linux
package managers.

**************************************
 Naming a pipx app in your own shebang
**************************************

The default pipx home on macOS is ``~/Library/Application Support/pipx``, which contains a space. Apps installed there
run because pip and uv write a ``/bin/sh`` wrapper as the shebang whenever the interpreter path holds a space.

A shebang you write yourself has no such wrapper. ``#!/Users/you/.local/bin/aws`` works, while a shebang naming a path
with a space does not, because the kernel reads the first space as the end of the interpreter path. Point your shebang
at ``PIPX_BIN_DIR`` (``~/.local/bin`` by default, no space), or set ``PIPX_HOME`` to a path without spaces.

********************************
 Does it install with plain pip?
********************************

To tell whether pipx or the package is at fault, try installing the package with pip.

Unix or macOS:

.. code-block:: console

    $ python3 -m venv test_venv
    $ test_venv/bin/python3 -m pip install <problem-package>

Windows:

.. code-block:: console

    $ python -m venv test_venv
    $ test_venv/Scripts/python -m pip install <problem-package>

If pip also fails, the problem is likely the package or your host. Clean up with ``rm -rf test_venv``.

**************************************
 Files not in the documented locations
**************************************

pipx after 1.16.0 places ``PIPX_HOME`` and the data, cache, and log directories in the platform locations
`platformdirs <https://pypi.org/project/platformdirs/>`_ reports. Earlier versions defaulted ``PIPX_HOME`` to
``~/.local/pipx`` (or ``~/pipx`` on Windows), and pipx keeps using such a directory when it exists. The venv cache and
logs still move to the platform cache and log directories even when pipx falls back to an older home, because both are
disposable. Setting ``PIPX_HOME`` yourself keeps them inside it.

For the full old-to-new path map and how to migrate, see :ref:`platformdirs-migration` and :doc:`move-installation`.

**********
 Verify it
**********

.. code-block:: console

    $ pipx health

A clean ``pipx health`` (exit status 0) confirms every managed environment can run its interpreter.
