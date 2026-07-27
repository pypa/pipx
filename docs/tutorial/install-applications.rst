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
      installed package httpie 3.2.4, Python 3.12.3
      These apps are now globally available
        - http
        - https
    done! ✨ 🌟 ✨

pipx creates a virtual environment, installs the ``httpie`` package into it, and exposes the apps it declares on your
``PATH``. Note that the package is ``httpie`` but the commands are ``http`` and ``https``: one package, two apps.

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
       package httpie 3.2.4, Python 3.12.3
        - http
        - https

************************
 Run it and verify
************************

Call one of the exposed apps to confirm the install:

.. code-block:: console

    $ http --version
    3.2.4

If the version prints, the app is on your ``PATH`` and ready to use. (Missing? Run ``pipx ensurepath`` and open a new
terminal, then see :doc:`Troubleshoot <../how-to/troubleshoot>`.)

************
 Learn more
************

``pipx install`` has more to offer once you outgrow the basics:

- :doc:`Expose apps <../how-to/expose-apps>`: hide or reveal commands with ``expose`` / ``unexpose``, and pull apps out
  of dependencies with ``--include-deps``.
- :doc:`Tool manifests <../how-to/tool-manifest>`: manage a set of tools with a ``pipx.toml`` manifest and PEP 751 lock
  files.
- :doc:`Run scripts <../how-to/run-scripts>`: install a local PEP 723 script as a managed app.
- :doc:`Use the uv backend <../how-to/use-uv-backend>`: swap pip for uv to resolve and install faster.
- :doc:`Standalone Python <../how-to/standalone-python>`: install against a specific Python version, downloading one if
  needed.
