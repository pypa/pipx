##########
 Examples
##########

Copy-paste command examples. For every flag see the :doc:`CLI reference <cli>`. For step-by-step narratives, follow the
how-to guides linked in each section.

*********
 install
*********

Install from PyPI, optionally pinning the Python version:

.. code-block:: bash

    pipx install pycowsay
    pipx install --python 3.12 pycowsay
    pipx install --fetch-python=missing --python 3.12 pycowsay

Constrain or eagerly upgrade a version spec:

.. code-block:: bash

    pipx install --upgrade 'black>=22,<23'
    pipx install --upgrade --upgrade-strategy eager 'black>=22,<23'

Install extras, include dependency apps, or preinstall build-time packages:

.. code-block:: bash

    pipx install 'black[d]'
    pipx install --include-deps jupyter
    pipx install --preinstall ansible-lint --preinstall mitogen ansible-core

Install from a VCS URL, an archive, or a local project:

.. code-block:: bash

    pipx install git+https://github.com/psf/black
    pipx install git+https://github.com/psf/black.git@branch-name
    pipx install https://github.com/psf/black/archive/18.9b0.zip
    pipx install ./path/to/some-project

Install from a PEP 723 script or a lock file:

.. code-block:: bash

    pipx install ./script.py
    pipx install --lock pylock.toml .

For a local script, the filename without its extension supplies the command name. Pass ``--app`` to choose a different
name:

.. code-block:: bash

    pipx install --app greet ./script.py

Pass arguments through to pip, or install globally for all users:

.. code-block:: bash

    pipx install --pip-args='--pre' poetry
    pipx install --global pycowsay

*****
 run
*****

Run an app in a temporary environment, optionally pinning package or Python version:

.. code-block:: bash

    pipx run pycowsay moo
    pipx run --spec 'pycowsay==0.0.0.2' pycowsay --version
    pipx run --python 3.12 pycowsay moo

Run from a VCS URL or an archive:

.. code-block:: bash

    pipx run git+https://github.com/psf/black.git
    pipx run --spec https://github.com/psf/black/archive/18.9b0.zip black --help

Run a local or remote script, with arguments:

.. code-block:: bash

    pipx run test.py 1 2 3
    pipx run https://example.com/test.py 1 2 3

A bare filename is ambiguous: pipx runs it as a local file when the file exists, otherwise as a PyPI package. Force the
interpretation with ``--path`` or ``--spec``:

.. code-block:: bash

    pipx run --path test.py         # always a local file
    pipx run --spec test-py test.py # always a PyPI package

Scripts can declare dependencies with PEP 723 inline metadata; pipx installs them into the temporary environment. See
:doc:`Run scripts <../how-to/run-scripts>`.

********
 inject
********

Add packages to an existing environment, from the command line or a requirements file:

.. code-block:: bash

    pipx inject ptpython requests pendulum
    pipx inject ptpython --requirement useful-packages.txt

The two forms can be combined and repeated:

.. code-block:: bash

    pipx inject ptpython package-1 package-2 -r extra-1.txt -r extra-2.txt

See :doc:`Inject packages <../how-to/inject-packages>` for the requirements-file format and the ``--include-apps``
option.

******
 list
******

List installed packages and their apps:

.. code-block:: console

    $ pipx list
    venvs are in /home/user/.local/share/pipx/venvs
    apps are exposed on your $PATH at /home/user/.local/bin
    manual pages are exposed at /home/user/.local/share/man
    shell completions are exposed at /home/user/.local/share
       package black 24.3.0, installed using Python 3.12.0
        - black
        - blackd
       package pipx 1.4.3, installed using Python 3.12.0
        - pipx

Narrow the output or change the format; the package filter works with every format:

.. code-block:: bash

    pipx list --short
    pipx list black pipx --short
    pipx list black --outdated
    pipx list --output json > pipx.json

*************
 install-all
*************

Reinstall from a snapshot produced by ``pipx list --output json`` (see :doc:`json-output`). Each environment gets the
venv and pip arguments the snapshot recorded unless you pass your own. A ``--backend`` other than the recorded one skips
the recorded pip arguments with a warning, since they can hold options only the old backend accepts. Options with an
exact equivalent are translated instead, so the environment still installs from the recorded index:

=============================== ======================================================
pip                             uv
=============================== ======================================================
``--index-url``, ``-i``         ``--default-index``
``--extra-index-url``           ``--index`` (a ``name=`` prefix is dropped for pip)
``--find-links``, ``-f``        ``--find-links`` (split on commas for pip)
``--no-index``                  ``--no-index``
``--pre``                       ``--prerelease allow``
``--trusted-host HOST``         ``--allow-insecure-host HOST``
``--constraint``, ``-c``        ``--constraints``
``--keyring-provider``          ``--keyring-provider`` (``disabled`` or ``subprocess``)
(always picks the best match)   ``--index-strategy unsafe-best-match``
=============================== ======================================================

A pip option recorded as an abbreviation pip accepts, such as ``--index-u``, is translated like its full spelling.
When a recorded index option has no equivalent, such as a uv ``--index-strategy`` other than ``unsafe-best-match``, an
``--allow-insecure-host`` URL, or pip's ``--keyring-provider import``, pipx refuses to install that environment rather
than fall back to PyPI. pip searches every index for the best version, while uv stops at the first index that has the
package, so a uv ``--index`` moved to pip can pick a newer release from PyPI. Pass ``--pip-args`` to replace the
recorded options. Up to eight environments install at once, with their output printed in snapshot order:

.. code-block:: console

    $ pipx install-all pipx.json
    'black' (24.3.0) already seems to be installed. Not
    modifying existing installation in '/home/user/.local/share/pipx/venvs/black'.
    Pass '--force' to force installation, or use
    'pipx upgrade black' to upgrade.
    'pipx' (1.4.3) already seems to be installed. Not
    modifying existing installation in '/home/user/.local/share/pipx/venvs/pipx'.
    Pass '--force' to force installation, or use
    'pipx upgrade pipx' to upgrade.
    $ pipx install-all pipx.json --force
    Installing to existing venv 'black'
      installed package black 24.3.0, installed using Python 3.12.0
      These apps are now available
        - black
        - blackd
    Installing to existing venv 'pipx'
      installed package pipx 1.4.3, installed using Python 3.12.0
      These apps are now available
        - pipx

***************
 upgrade-shared
***************

Upgrade the shared libraries now, instead of waiting for the automatic refresh once they are more than 30 days old:

.. code-block:: bash

    pipx upgrade-shared

*********
 pin
*********

Pin an environment so its packages are held at their current versions until you unpin. See :doc:`Pin packages
<../how-to/pin-packages>`.

Pin only injected packages, leaving the main package upgradable:

.. code-block:: console

    $ pipx pin poetry --injected-only
    pipx pinned 2 packages in venv poetry
      - poetry-plugin-export <current version>
      - poetry-plugin-app <current version>

Unpin the environment so upgrades resume. Only packages that were pinned are listed:

.. code-block:: console

    $ pipx unpin poetry
    pipx unpinned 2 packages in venv poetry
      - poetry-plugin-export
      - poetry-plugin-app
