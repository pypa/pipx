##################
 Move installation
##################

Relocate your pipx directory to a new location and rebuild the environments there.

The snippets below move from a non-default location to the current default. To move somewhere else, replace the
``NEW_LOCATION`` value. For which paths pipx defaults to and why they moved, see :ref:`platformdirs-migration`.

.. warning::

    The macOS and Linux snippets clear the cache, log, and trash directories. Pipx recreates them. Each snippet
    includes ``pipx reinstall-all`` to rebuild the environments at the new location.

******
 macOS
******

Current default location: ``~/Library/Application Support/pipx``.

.. code-block:: bash

    cache_dir=$(pipx environment --value PIPX_VENV_CACHEDIR)
    logs_dir=$(pipx environment --value PIPX_LOG_DIR)
    trash_dir=$(pipx environment --value PIPX_TRASH_DIR)
    home_dir=$(pipx environment --value PIPX_HOME)
    NEW_LOCATION="$HOME/Library/Application Support"
    rm -rf "$cache_dir" "$logs_dir" "$trash_dir"
    mkdir -p "$NEW_LOCATION" && mv "$home_dir" "$NEW_LOCATION"
    pipx reinstall-all

******
 Linux
******

Current default location: ``~/.local/share/pipx`` (``$XDG_DATA_HOME/pipx`` when set).

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

Current default location: ``%LOCALAPPDATA%\pipx\pipx``. Set ``$home_dir`` to your current pipx home. The example
uses the legacy ``%USERPROFILE%\pipx`` location. For a custom destination, use an absolute path on the same drive.

Pipx may have created the default destination for logs or cache files. If it holds only those files, rename the
directory to an unused name before running the example. For any other contents, choose a different destination.

.. code-block:: powershell

    & {
        $ErrorActionPreference = 'Stop'
        $home_dir = Join-Path $env:USERPROFILE 'pipx'
        $NEW_LOCATION = Join-Path $env:LOCALAPPDATA 'pipx\pipx'
        if (Test-Path -LiteralPath $NEW_LOCATION) {
            throw "The destination already exists: $NEW_LOCATION. Choose an unused directory."
        }

        [System.IO.Directory]::CreateDirectory((Split-Path -Parent $NEW_LOCATION)) | Out-Null
        [System.IO.Directory]::Move($home_dir, $NEW_LOCATION)

        $env:PIPX_HOME = $NEW_LOCATION
        pipx reinstall-all
    }

The example sets ``PIPX_HOME`` for the current session. Save the new path in your user environment variables if
you have a custom destination, a saved ``PIPX_HOME``, or a remaining :ref:`legacy home <platformdirs-migration>`.

From Git Bash or WSL, open Windows PowerShell and follow these steps to move a Windows pipx installation.

**********
 Verify it
**********

.. code-block:: console

    $ pipx environment --value PIPX_HOME
    $ pipx list

The home path reflects the new location and every environment lists cleanly after the reinstall.
