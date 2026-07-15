#####################
 Getting started
#####################

This tutorial covers the core pipx workflow: install an application, run it, upgrade it, and remove it. Work through it
top to bottom with one small package, and you will know every command you need day to day.

.. note::

    Install pipx first. See :doc:`Install pipx <../how-to/install-pipx>`.

*******************
 Packages and apps
*******************

pipx installs **packages** and exposes their **apps**. A package is what you download from PyPI, such as ``pycowsay`` or
``httpie``. An app is a command that package puts on your ``PATH`` through a `console script entry point
<https://packaging.python.org/en/latest/specifications/entry-points/>`_. One package can expose several apps: ``httpie``
gives you both ``http`` and ``https``. For the full picture, see :doc:`How pipx works <../explanation/how-pipx-works>`.

***************
 The lifecycle
***************

.. mermaid::

    flowchart LR
        INSTALL["pipx install"] --> LIST["pipx list"]
        LIST --> RUN["run the app"]
        RUN --> UPGRADE["pipx upgrade"]
        UPGRADE --> UNINSTALL["pipx uninstall"]

        classDef step fill:#2a9d8f,stroke:#1f7268,color:#fff;
        class INSTALL,LIST,RUN,UPGRADE,UNINSTALL step;

****************************
 Install your first app
****************************

Pick a small package to try. ``pycowsay`` works well:

.. code-block:: console

    $ pipx install pycowsay
      installed package pycowsay 2.0.3, Python 3.10.3
      These apps are now globally available
        - pycowsay
    done! ✨ 🌟 ✨

pipx creates an isolated virtual environment for ``pycowsay``, installs it there, and links the ``pycowsay`` command into
a directory on your ``PATH``. No ``sudo`` required.

Confirm it worked
=================

Run the app from anywhere:

.. code-block:: console

    $ pycowsay moo
      ---
    < moo >
      ---
       \   ^__^
        \  (oo)\_______
           (__)\       )\/\
               ||----w |
               ||     ||

If you see the cow, pipx is working.

.. tip::

    ``pycowsay: command not found``? pipx installed the app but its directory is not on your ``PATH`` yet. Run ``pipx
    ensurepath``, then open a new terminal. See :doc:`Install pipx <../how-to/install-pipx>` and :doc:`Troubleshoot
    <../how-to/troubleshoot>` if it persists.

****************************
 List installed apps
****************************

.. code-block:: console

    $ pipx list
    venvs are in /home/user/.local/share/pipx/venvs
    apps are exposed on your $PATH at /home/user/.local/bin
       package pycowsay 2.0.3, Python 3.10.3
        - pycowsay

The output shows each virtual environment's location, the apps it exposes, and the Python version it uses.

**********************************
 Run an app without installing
**********************************

``pipx run`` executes an app in a temporary environment and cleans up after itself:

.. code-block:: console

    $ pipx run pycowsay moo

Reach for this when you want to try a tool once. The :doc:`run-applications` tutorial covers it in depth.

****************
 Upgrade an app
****************

Upgrade a single app to its latest release:

.. code-block:: console

    $ pipx upgrade pycowsay

Or upgrade everything at once:

.. code-block:: console

    $ pipx upgrade-all

.. tip::

    See what has an update before upgrading with ``pipx list --outdated``. The output lists each package's installed and
    available versions.

******************
 Uninstall an app
******************

.. code-block:: console

    $ pipx uninstall pycowsay

pipx deletes the isolated environment and removes the command from your ``PATH``, leaving nothing behind.

************
 Next steps
************

- :doc:`install-applications`: install a real tool with ``pipx install``.
- :doc:`run-applications`: run apps in throwaway environments with ``pipx run``.
- :doc:`How-to guides <../how-to/index>`: inject packages, pin versions, configure paths, and more.
- :doc:`../reference/cli`: every command and flag.

.. tip::

    Scripting pipx? Most commands accept ``--output json``. See :doc:`JSON output <../reference/json-output>`.
