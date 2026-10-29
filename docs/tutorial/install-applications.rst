##########################
 Installing applications
##########################

:doc:`getting-started` walked through the ``install`` → ``list`` → ``run`` → ``uninstall`` cycle with the toy
``pycowsay`` package. This tutorial repeats it with a real tool so you can see how a package's name and its apps differ.

****************
 Install a tool
****************

Install `HTTPie <https://httpie.io/>`_, a command-line HTTP client:

.. code-block:: console

    $ pipx install httpie
      installed package httpie 3.2.4, installed using Python 3.12.3
      These apps are now available
        - http
        - httpie
        - https
      These manual pages are now available
        - man1/http.1
        - man1/httpie.1
        - man1/https.1
    done! ✨ 🌟 ✨

pipx creates a virtual environment, installs the ``httpie`` package into it, and exposes the apps it declares on your
``PATH``. The package is ``httpie``, but it exposes three apps: ``http``, ``httpie``, and ``https``.

.. tip::

    To install a tool for every user on the system, pass ``--global``. See :doc:`Configure paths
    <../how-to/configure-paths>`.

*******************
 See what you got
*******************

.. code-block:: console

    $ pipx list
    venvs are in /home/user/.local/share/pipx/venvs
    apps are exposed on your $PATH at /home/user/.local/bin
    manual pages are exposed at /home/user/.local/share/man
    shell completions are exposed at /home/user/.local/share
       package httpie 3.2.4, installed using Python 3.12.3
        - http
        - httpie
        - https
        - man1/http.1
        - man1/httpie.1
        - man1/https.1

************************
 Run it and verify
************************

Call one of the exposed apps to confirm the install:

.. code-block:: console

    $ http --version
    3.2.4

If the version prints, the app is on your ``PATH`` and ready to use. (Missing? Run ``pipx ensurepath`` and open a new
terminal, then see :doc:`Troubleshoot <../how-to/troubleshoot>`.)

*************************
 Hold back fresh releases
*************************

The newest release is the one most likely to ship a bug or a compromise. Install the next tool a week behind the index:

.. code-block:: console

    $ pipx install --cooldown 7 black
      installed package black 24.8.0, installed using Python 3.12.3
      These apps are now available
        - black
        - blackd
    done! ✨ 🌟 ✨

pipx remembers the number, so later upgrades of ``black`` keep the same seven-day lag without you repeating the flag.
Set ``PIPX_COOLDOWN=7`` in your shell profile to get the same lag for every tool.

************
 Learn more
************

More on ``pipx install``:

- :doc:`Expose apps <../how-to/expose-apps>`: hide or reveal commands with ``expose`` / ``unexpose``, and pull apps out
  of dependencies with ``--include-deps``.
- :doc:`Tool manifests <../how-to/tool-manifest>`: manage a set of tools with a ``pipx.toml`` manifest and :pep:`751`
  lock files.
- :doc:`Run scripts <../how-to/run-scripts>`: install a local :pep:`723` script as a managed app.
- :doc:`Use the uv backend <../how-to/use-uv-backend>`: swap `pip <https://pip.pypa.io>`_ for `uv
  <https://docs.astral.sh/uv/>`_ to resolve and install faster.
- :doc:`Standalone Python <../how-to/standalone-python>`: install against a specific Python version, downloading one if
  needed.
- :doc:`Dependency cooldown <../how-to/dependency-cooldown>`: set the release-age lag once with ``PIPX_COOLDOWN``.
