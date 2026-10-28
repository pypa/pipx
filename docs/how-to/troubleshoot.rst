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

If the package is already installed, reinstall it instead; ``pipx install --force`` ignores ``--python``:

.. code-block:: console

    $ pipx reinstall my-package --python python3.12

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
subset, or ``--output json`` to read the result from a script; each unhealthy environment then appears in ``errors``
with the code ``environment_unhealthy``.

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

    Do the same for an environment whose record is missing because its install was killed, or unreadable because a newer
    pipx wrote it: ``pipx reinstall``, ``pipx reinstall-all`` and ``pipx repair`` refuse it rather than guess its
    source.

********************************
 Start over from a fresh install
********************************

An interrupted install or shared-library upgrade can leave state that ``pipx repair`` cannot mend. Reset pipx to the
state it had at install time:

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

Under the pip backend, ``PIP_*`` environment variables change how pipx installs and upgrades packages. If pipx behaves
strangely on install or upgrade, check for them.

Unix or macOS:

.. code-block:: console

    $ env | grep '^PIP_'

Windows PowerShell:

.. code-block:: console

    $ ls env:PIP_*

Windows ``cmd``:

.. code-block:: console

    $ set PIP_

See `pip's environment variables <https://pip.pypa.io/en/stable/user_guide/#environment-variables>`_. The uv backend
ignores ``PIP_*`` and reads uv's own ``UV_*`` variables (for example ``UV_INDEX_URL``) instead; check for those the same
way.

****************************
 Clear runpip cache warnings
****************************

Under the pip backend, ``pipx runpip`` runs pip from pipx's shared libraries with a pipx-managed venv's interpreter.
Warnings such as ``WARNING: Cache entry deserialization failed, entry ignored`` come from that pip and its own HTTP
cache, not from pipx's venv cache.

Inspect and clear the cache for a managed package:

.. code-block:: console

    $ pipx runpip <package> cache dir
    $ pipx runpip <package> cache purge

Clearing pipx's venv cache (``pipx environment --value PIPX_VENV_CACHEDIR``) or the cache for a different interpreter
does not clear entries used by ``pipx runpip <package>``.

Under the uv backend, ``pipx runpip`` runs ``uv pip``, which has no ``cache`` subcommand. Use uv's cache commands with
the binary pipx uses (``pipx environment --value PIPX_UV_BINARY``):

.. code-block:: console

    $ uv cache dir
    $ uv cache clean

**********
 Log files
**********

pipx writes a verbose log for every command to ``pipx environment --value PIPX_LOG_DIR``. By default that is
``~/.local/state/pipx/log`` on Linux (``$XDG_STATE_HOME/pipx/log``), ``~/Library/Logs/pipx`` on macOS, and
``%LOCALAPPDATA%\pipx\pipx\Logs`` on Windows, or ``$PIPX_HOME/logs`` when ``PIPX_HOME`` is set. When that directory is
not writable, pipx falls back to the platform user log directory. A command that fails while pip or uv runs also writes
the backend output beside its log, as ``cmd_<timestamp>_pip_errors.log`` or ``cmd_<timestamp>_uv_errors.log``.

pipx keeps the logs of the last 10 commands, counting the one that is running, and separately the last 10 error logs.
Set ``PIPX_MAX_LOGS`` to change both limits. ``0`` acts like ``1``: the latest command's log stays, because a failing
command points you at its error log. pipx never deletes the logs of a command that is still running in another pipx
process, so concurrent commands can briefly leave more logs than the limit.

****************************
 Lazy imports on Python 3.15
****************************

On Python 3.15 pipx makes every import in its process lazy (:pep:`810`) to start faster. A missing or broken dependency
then fails where pipx first uses it, with ``lazy import of 'X' raised an exception during resolution``, instead of at
startup. To load modules eagerly, set ``PYTHON_LAZY_IMPORTS=normal`` or run ``python -X lazy_imports=normal -m pipx``;
pipx keeps a mode you set either way.

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

*************************************
 A suffixed app runs under a new name
*************************************

pipx 1.17.14 and earlier put ``--suffix`` before the last dot of an app name, so ``pipx install pip --suffix=_old``
exposed ``pip3_old.12``. Later releases put it at the end, ``pip3.12_old``; on Windows it still goes before a file
extension such as ``.exe`` or ``.py``, so the file keeps opening. After you upgrade pipx, an app keeps its old name and
``pipx list`` shows it under that name. The next ``pipx upgrade``, ``reinstall``, ``inject``, or ``expose`` of the
environment renames it and logs ``Renamed pip3_old.12 to pip3.12_old``. Update scripts and aliases that call the old
name.

******************************************
 ``Cannot create ...: permission denied``
******************************************

pipx creates its home, binary, and manual page directories before any command that may write to them. When the current
user cannot create one, pipx exits with this error and names the directory. With ``--global`` the defaults sit under
``/opt/pipx`` and ``/usr/local``, so run the command with ``sudo``. Otherwise, or to keep the installation out of
system directories, point ``PIPX_HOME``, ``PIPX_BIN_DIR``, and ``PIPX_MAN_DIR`` (or their ``PIPX_GLOBAL_*``
counterparts) at directories you can write; see :doc:`configure-paths`.

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
