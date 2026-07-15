##################
 Move installation
##################

Relocate your pipx directory to a new location and rebuild the environments there.

The snippets below move from a non-default location to the current default. To move somewhere else, replace the
``NEW_LOCATION`` value. For which paths pipx defaults to and why they moved, see :ref:`platformdirs-migration`.

.. warning::

    These snippets delete the cache, log, and trash directories (pipx recreates them) and move ``PIPX_HOME``. Run
    ``pipx reinstall-all`` afterward so every environment rebuilds at the new location.

******
 macOS
******

Current default location: ``~/Library/Application Support/pipx``.

.. code-block:: bash

    cache_dir=$(pipx environment --value PIPX_VENV_CACHEDIR)
    logs_dir=$(pipx environment --value PIPX_LOG_DIR)
    trash_dir=$(pipx environment --value PIPX_TRASH_DIR)
    home_dir=$(pipx environment --value PIPX_HOME)
    NEW_LOCATION='~/Library/Application Support/pipx'
    rm -rf "$cache_dir" "$logs_dir" "$trash_dir"
    mkdir -p "$NEW_LOCATION" && mv "$home_dir" "$NEW_LOCATION"
    pipx reinstall-all

******
 Linux
******

Current default location: ``~/.local/share``.

.. code-block:: bash

    cache_dir=$(pipx environment --value PIPX_VENV_CACHEDIR)
    logs_dir=$(pipx environment --value PIPX_LOG_DIR)
    trash_dir=$(pipx environment --value PIPX_TRASH_DIR)
    home_dir=$(pipx environment --value PIPX_HOME)
    NEW_LOCATION="${XDG_DATA_HOME:-$HOME/.local/share}"
    rm -rf "$cache_dir" "$logs_dir" "$trash_dir"
    mkdir -p "$NEW_LOCATION" && mv "$home_dir" "$NEW_LOCATION"
    pipx reinstall-all

********
 Windows
********

Current default location: ``~/pipx``.

.. code-block:: powershell

    $NEW_LOCATION = Join-Path "$HOME" 'pipx'
    $cache_dir = pipx environment --value PIPX_VENV_CACHEDIR
    $logs_dir = pipx environment --value PIPX_LOG_DIR
    $trash_dir = pipx environment --value PIPX_TRASH_DIR
    $home_dir = pipx environment --value PIPX_HOME

    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$cache_dir", "$logs_dir", "$trash_dir"

    # Remove the destination first so Move-Item renames rather than nests
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$NEW_LOCATION"

    Move-Item -Path $home_dir -Destination "$NEW_LOCATION"
    pipx reinstall-all

To move it from git-bash or WSL instead, follow the macOS/Linux steps and set ``NEW_LOCATION`` to the Windows path.

**********
 Verify it
**********

.. code-block:: console

    $ pipx environment --value PIPX_HOME
    $ pipx list

The home path reflects the new location and every environment lists cleanly after the reinstall.
