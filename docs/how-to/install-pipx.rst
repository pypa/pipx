#############
 Install pipx
#############

Get pipx onto your system and add its app directory to your ``PATH``.

pipx runs on macOS, Linux, and Windows.

.. image:: https://repology.org/badge/vertical-allrepos/pipx.svg?columns=3&exclude_unsupported=1
    :target: https://repology.org/metapackage/pipx/versions
    :alt: Packaging status

***********************
 Check the requirements
***********************

Installing pipx needs Python 3.10 or newer; the apps it runs can target Python 3.3 or newer. Without Python 3.10, see
the `Python 3 installation guide <https://realpython.com/installing-python/>`_.

You also need ``pip`` for ``python3``. The steps vary by system; see `pip's installation instructions
<https://pip.pypa.io/en/stable/installation/>`_. On Linux, install through a `Linux package manager
<https://packaging.python.org/guides/installing-using-linux-tools/#installing-pip-setuptools-wheel-with-linux-package-managers>`_.

***************
 Install per OS
***************

macOS
=====

.. code-block:: console

    $ brew install pipx
    $ pipx ensurepath

Linux
=====

Ubuntu 23.04 or newer:

.. code-block:: console

    $ sudo apt update
    $ sudo apt install pipx
    $ pipx ensurepath

Fedora:

.. code-block:: console

    $ sudo dnf install pipx
    $ pipx ensurepath

Other distributions, using ``pip``:

.. code-block:: console

    $ python3 -m pip install --user pipx
    $ python3 -m pipx ensurepath

.. warning::

    Distributions that adopt `PEP 668 <https://peps.python.org/pep-0668/>`_ (Ubuntu 23.04+, Debian 12+, Fedora 38+) mark
    the system Python as externally managed, so ``pip install --user`` fails with ``externally-managed-environment``. Use
    the distribution package (``apt install pipx``, ``dnf install pipx``). If none exists, install pipx into its own
    virtual environment:

    .. code-block:: console

        $ python3 -m venv ~/.local/share/pipx-venv
        $ ~/.local/share/pipx-venv/bin/pip install pipx
        $ ln -s ~/.local/share/pipx-venv/bin/pipx ~/.local/bin/pipx
        $ pipx ensurepath

Windows
=======

Install via `Scoop <https://scoop.sh/>`_:

.. code-block:: console

    $ scoop install pipx
    $ pipx ensurepath

Install via pip (needs pip 19.0 or newer; replace ``py`` with ``python3`` if you installed Python from the Microsoft
Store):

.. code-block:: console

    $ py -m pip install --user pipx

This often ends with a warning that ``pipx.exe`` is installed in a directory that is not on ``PATH``. Go to that
directory and run the executable directly to fix it (run this even without the warning):

.. code-block:: console

    $ .\pipx.exe ensurepath

This adds both that directory and ``%USERPROFILE%\.local\bin`` to your search path. Restart the terminal, then confirm
``pipx`` runs.

FreeBSD
=======

.. code-block:: console

    $ pkg install -y py311-pipx
    $ pipx ensurepath

Or via pip:

.. code-block:: console

    $ pip install --user pipx
    $ pipx ensurepath

***********************
 Optional PATH commands
***********************

Add the global app directory to the system ``PATH`` (pipx 1.5.0+):

.. code-block:: console

    $ sudo pipx ensurepath --global

Prepend the pipx bin directory instead of appending it, so pipx apps win over system apps of the same name (pipx
1.7.0+):

.. code-block:: console

    $ sudo pipx ensurepath --prepend

For where these directories live and how to change them, see :doc:`configure-paths`.

.. note::

    Some distributions ship older pipx versions (Ubuntu 24.04 ships 1.4.3). If ``--global`` or ``--prepend`` fails with
    "unrecognized arguments", :doc:`upgrade pipx <upgrade-pipx>` first.

.. tip::

    ``sudo pipx`` reports "command not found" when pipx lives in your user directory. See :ref:`sudo-pipx-not-found` for
    the fix.

****************************
 Run pipx without installing
****************************

Download the zipapp from `GitHub releases <https://github.com/pypa/pipx/releases>`_ and invoke it with a Python 3.10+
interpreter:

.. code-block:: console

    $ python pipx.pyz ensurepath

******************
 Self-managed pipx
******************

Let pipx manage its own installation so ``pipx upgrade pipx`` keeps it current and you avoid distro packages that ship
older versions. Bootstrap it through a throwaway virtual environment:

.. code-block:: console

    $ python3 -m venv /tmp/bootstrap
    $ /tmp/bootstrap/bin/pip install pipx
    $ /tmp/bootstrap/bin/pipx install pipx
    $ /tmp/bootstrap/bin/pipx ensurepath
    $ rm -rf /tmp/bootstrap

After this, ``pipx upgrade pipx`` upgrades pipx like any other managed app. On Windows, pipx cannot delete its own
running executable, so it moves locked files to a trash directory and cleans them up on the next run.

.. _install-from-source-control:

****************************
 Install from source control
****************************

pipx accepts any source pip supports, including git repositories. Using ``black`` as an example:

.. code-block:: console

    $ pipx install git+https://github.com/psf/black.git
    $ pipx install git+ssh://git@github.com/psf/black
    $ pipx install git+https://github.com/psf/black.git@branch
    $ pipx install git+https://github.com/psf/black.git@ce14fa8b497bae2b50ec48b3bd7022573a59cdb1
    $ pipx install https://github.com/psf/black/archive/18.9b0.zip

Use pip's ``egg`` syntax to install extras:

.. code-block:: console

    $ pipx install "git+https://github.com/psf/black.git#egg=black[jupyter]"

To test a package from an open pull request, find the fork owner and branch on the PR page, then build the git URL. For
PR #794 from user ``contributor`` on branch ``fix-something``:

.. code-block:: console

    $ pipx install git+https://github.com/contributor/pipx.git@fix-something

If the branch is already merged, use the merge commit hash instead:

.. code-block:: console

    $ pipx install git+https://github.com/pypa/pipx.git@abc123def

**********
 Verify it
**********

.. code-block:: console

    $ pipx --version

Open a new terminal after ``pipx ensurepath`` so the updated ``PATH`` takes effect, then run ``pipx list`` to confirm
the environment is reachable.
