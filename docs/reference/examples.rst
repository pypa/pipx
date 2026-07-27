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
    pipx run --spec 'pycowsay==2.0' pycowsay --version
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

    pipx inject ptpython package-1 -r extra-1.txt -r extra-2.txt package-2

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
       package black 24.3.0, Python 3.12.0
        - black
        - blackd
       package pipx 1.4.3, Python 3.12.0
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

Reinstall from a snapshot produced by ``pipx list --output json`` (see :doc:`json-output`):

.. code-block:: console

    $ pipx install-all pipx.json
    'black' already seems to be installed. Not modifying existing installation in '/usr/local/pipx/venvs/black'. Pass '--force' to force installation.
    'pipx' already seems to be installed. Not modifying existing installation in '/usr/local/pipx/venvs/pipx'. Pass '--force' to force installation.
    $ pipx install-all pipx.json --force
    Installing to existing venv 'black'
      installed package black 24.3.0, installed using Python 3.12.0
      These apps are now globally available
        - black
        - blackd
    Installing to existing venv 'pipx'
      installed package pipx 1.4.3, installed using Python 3.12.0
      These apps are now globally available
        - pipx

***************
 upgrade-shared
***************

Upgrade the shared libraries, or pin pip to a specific version until the next automatic upgrade:

.. code-block:: bash

    pipx upgrade-shared
    pipx upgrade-shared --pip-args=pip==24.0

*********
 pin
*********

Pin an environment so its packages are held at their current versions until you unpin. See :doc:`Pin packages
<../how-to/pin-packages>`.

Pin only injected packages, leaving the main package upgradable:

.. code-block:: console

    $ pipx pin poetry --injected-only
    Pinned 2 packages in venv poetry
      - poetry-plugin-export <current version>
      - poetry-plugin-app <current version>

Unpin the whole environment so upgrades resume:

.. code-block:: console

    $ pipx unpin poetry
    Unpinned 3 packages in venv poetry
      - poetry
      - poetry-plugin-export
      - poetry-plugin-app
