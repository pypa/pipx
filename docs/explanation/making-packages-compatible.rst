##############################
 Making packages compatible
##############################

*********************
 Developing for pipx
*********************

This page helps developers to make their packages more pipx-friendly, making sure that apps, manual pages,
shell completion scripts provided by the package are automatically *exposed* (made available) to the end
user after running:

.. code-block:: console

    $ pipx install MY_PACKAGE

Package apps
============

To make sure that apps provided by the package are exposed, just include a ``project.scripts`` table
in your ``pyproject.toml`` file, or use the ``setuptools`` legacy ``entry_points`` equivalents in
``setup.cfg`` or ``setup.py`` (see examples below).

pipx also exposes ``gui-scripts`` entry points, which are useful for GUI applications on
Windows (they launch without opening a console window).

.. tab-set::

    .. tab-item:: pyproject.toml

        .. code-block:: toml

            [project.scripts]
            foo = "my_package.some_module:main_func"
            bar = "other_module:some_func"

            [project.gui-scripts]
            baz = "my_package_gui:start_func"

    .. tab-item:: setup.cfg

        .. code-block:: ini

            [options.entry_points]
            console_scripts =
                foo = my_package.some_module:main_func
                bar = other_module:some_func
            gui_scripts =
                baz = my_package_gui:start_func

    .. tab-item:: setup.py

        .. code-block:: python

            setup(
                # other arguments here...
                entry_points={
                    "console_scripts": [
                        "foo = my_package.some_module:main_func",
                        "bar = other_module:some_func",
                    ],
                    "gui_scripts": [
                        "baz = my_package_gui:start_func",
                    ],
                },
            )

Here ``foo``, ``bar``, and ``baz`` become applications that pipx exposes after installing the
package, invoking their corresponding entry point functions. This is implemented by installing
proper executable scripts in ``PIPX_BIN_DIR`` (default: ``~/.local/bin``).

.. mermaid::

    flowchart LR
        TOML["pyproject.toml<br/>[project.scripts]"] -->|defines| EP["entry points<br/>foo, bar"]
        EP -->|pipx install| VENV["isolated venv"]
        VENV -->|symlink or copy| BIN["~/.local/bin/<br/>foo, bar"]
        BIN -->|invokes| FUNC["my_package:<br/>main_func()"]

        classDef input fill:#3f72af,stroke:#28517f,color:#fff
        classDef proc fill:#2a9d8f,stroke:#1c6b61,color:#fff
        classDef venv fill:#7c4dff,stroke:#5a2fd0,color:#fff
        classDef out fill:#388e3c,stroke:#256128,color:#fff
        classDef fn fill:#c78c20,stroke:#8a6011,color:#fff
        class TOML input
        class EP proc
        class VENV venv
        class BIN out
        class FUNC fn

The ``pipx.run`` entry point group
==================================

When a user runs ``pipx run PACKAGE``, pipx looks for a console script matching the package name. If the package name
and script name differ, the user has to write ``pipx run --spec PACKAGE SCRIPT``, which is less convenient.

Package authors can declare a ``pipx.run`` entry point group to tell pipx which function to invoke for ``pipx run``.
This entry point takes priority over console scripts when present.

.. tab-set::

    .. tab-item:: pyproject.toml

        .. code-block:: toml

            [project.entry-points."pipx.run"]
            my-package = "my_package.cli:main"

    .. tab-item:: setup.cfg

        .. code-block:: ini

            [options.entry_points]
            pipx.run =
                my-package = my_package.cli:main

With this declaration, ``pipx run my-package`` invokes ``my_package.cli:main`` even if no console script named
``my-package`` exists. The `build <https://github.com/pypa/build>`__ package uses this pattern so that ``pipx run build``
works even though ``build`` names its console script ``pyproject-build``.

.. warning::

    The pipx `uv` backend hands ``pipx run build`` to ``uv tool run``, which reads console scripts only, so
    this needs ``--backend pip`` there (see :doc:`../how-to/use-uv-backend`).

Read more about entry points in the `setuptools quickstart
<https://setuptools.pypa.io/en/latest/userguide/quickstart.html#entry-points-and-automatic-script-creation>`__.

Manual pages and shell completions
==================================

On UNIX-like systems, pipx can also expose ``man`` pages and shell completion scripts for the apps
provided by the package; those should be shipped in the package as *data files*, that will be
installed in a ``share/`` directory in the python virtual environment used for the package.

.. note::

    Shell completion scripts are supported by pipx starting from version 1.16.0.

At install time, pipx will install the data files and make sure that these are correctly *exposed*,
so that the ``man`` command can find the provided man pages, and the user's shell can use the
completion script for the apps provided by the package. This is implemented by symlinking them into
the proper directories: ``PIPX_MAN_DIR`` (default: ``~/.local/share/man``) and
``PIPX_COMPLETION_DIR`` (default: ``~/.local/share``).

.. list-table::
    :header-rows: 1
    :widths: 40 40 20

    - - Shipped by the package
      - Exposed to
      - Used by
    - - ``share/man/``
      - ``~/.local/share/man/``
      - man
    - - ``share/bash-completion/completions/``
      - ``~/.local/share/bash-completion/completions/``
      - bash
    - - ``share/fish/vendor_completions.d/``
      - ``~/.local/share/fish/vendor_completions.d/``
      - fish
    - - ``share/zsh/site-functions/``
      - ``~/.local/share/zsh/site-functions/``
      - zsh

.. note::
    Completion scripts for ``zsh`` require a change in the user's ``~/.zshrc`` to be activated, see
    the instructions in :doc:`../how-to/shell-completions`

Data files are included in python wheel packages using the standard *packagename-version.data/data* directory,
as defined by the `wheel distribution format
<https://packaging.python.org/en/latest/specifications/binary-distribution-format/#the-data-directory>`__.

Below you can find configuration examples for different *build backends* to make sure that data files
are packaged into the proper directories, so that pipx will be able to find them, install them
and expose them correctly.

The examples assume that the package build procedure creates data files in a ``build`` subtree
having the same structure that will be replicated in the root of the python environment:

.. code-block:: text

  ./build
      |
      /share
        |
        /man/man1/myapp.1
        |
        /bash-completion/completions/myapp
        |
        /fish/vendor_completions.d/myapp.fish
        |
        /zsh/site-functions/_myapp

This is the easiest way to make sure that data files will be installed in the correct locations, it
requires minimal configuration and it's supported by all major build backends (some of them actually
*require* it, others allow for greater flexibility in file arrangement, see the notes below).

.. tab-set::

    .. tab-item:: setuptools

        .. code-block:: toml

            # pyproject.toml
            [tool.setuptools.data-files]
            "share/man/man1" = ["build/share/man/man1/myapp.1"]
            "share/bash-completion/completions" = ["build/share/bash-completion/completions/myapp"]
            "share/fish/vendor_completions.d" = ["build/share/fish/vendor_completions.d/myapp.fish"]
            "share/zsh/site-functions" = ["build/share/zsh/site-functions/_myapp"]

        .. code-block:: ini

            # setup.cfg
            [options.data_files]
            share/man/man1 = build/share/man/man1/myapp.1
            share/bash-completion/completions = build/share/bash-completion/completions/myapp
            share/fish/vendor_completions.d = build/share/fish/vendor_completions.d/myapp.fish
            share/zsh/site-functions = build/share/zsh/site-functions/_myapp

        .. code-block:: python

            # setup.py
            setup(
                data_files=[
                    ("share/man/man1", ["build/share/man/man1/myapp.1"]),
                    ("share/bash-completion/completions", ["build/share/bash-completion/completions/myapp"]),
                    ("share/fish/vendor_completions.d", ["build/share/fish/vendor_completions.d/myapp.fish"]),
                    ("share/zsh/site-functions", ["build/share/zsh/site-functions/_myapp"])
                ],
            )

        .. note::

            ``setuptools`` requires a configuration setting *for each data file*, there is no way to
            configure the whole ``share`` tree as a data file source. Also, the `setuptools documentation
            <https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#setuptools-specific-configuration>`__
            calls the ``data-files`` keyword "discouraged", but it has no alternative when you need to ship files to
            be installed in the target environment but outside the package tree.

    .. tab-item:: pdm-backend

        .. code-block:: toml

            # pyproject.toml
            [tool.pdm.build]
            source-includes = ["build/share"]

            [tool.pdm.build.wheel-data]
            data = [
              { path = "build/share/**/*", relative-to = "build/" },
            ]

        .. note::

            Optionally, ``pdm-backend`` allows to use more ``{ path = ... }`` directives, if you prefer
            to map each data file/directory explicitly.

            For more information and examples, see: `PDM-Backend - Wheel data files
            <https://backend.pdm-project.org/build_config/#wheel-data-files>`__

    .. tab-item:: uv_build

        .. code-block:: toml

            # pyproject.toml
            [tool.uv.build-backend]
            data = { data = "build" }

        .. note::

            ``uv_build`` requires to indicate the directory *whose contents* will be shipped
            (i.e. ``build`` in our example, so that the ``share`` subtree will be shipped).

            For more information and examples, see:

            * `The uv build backend - file inclusion and exclusion
              <https://docs.astral.sh/uv/concepts/build-backend/#file-inclusion-and-exclusion>`__
            * `The uv build backend - the "data" setting
              <https://docs.astral.sh/uv/reference/settings/#build-backend_data>`__

    .. tab-item:: hatchling.build

        .. code-block:: toml

            # pyproject.toml
            #
            # Include the "build/share" tree in the sdist package; this is needed
            # since "build" is usually in .gitignore, so it would be excluded from
            # the package
            [tool.hatch.build.targets.sdist]
            artifacts = ["build/share"]

            # Include the "share" subtree in the wheel data.data dir
            [tool.hatch.build.targets.wheel.shared-data]
            "build/share" = "share"

        .. note::

            ``hatchling.build`` also allows to freely arrange the data files in the package building
            environment and map each file to its specific destination.

            For more information and examples, see:

            * `hatch - Build configuration <https://hatch.pypa.io/latest/config/build/>`__
            * `hatch - Wheel builder <https://hatch.pypa.io/latest/plugins/builder/wheel/>`__

Detect a pipx installation
==========================

The ``pipx_metadata.json`` file at the root of each environment in which a package is installed
by pipx, contains information about the environment itself, e.g. its name, apps and dependencies names and
paths, etc. Developers can use this information in their code to provide more specific messages to the user
(e.g. mentioning the name of the environment where the package is currently installed).

The following example shows how a developer can query pipx metadata for the environment name, which
can then be used to give pipx-specific recovery instructions to the user:

.. code-block:: python

    import json
    import sys
    from pathlib import Path


    def pipx_environment() -> str | None:
        try:
            metadata = json.loads((Path(sys.prefix) / "pipx_metadata.json").read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        environment = metadata.get("environment") if isinstance(metadata, dict) else None
        return environment if isinstance(environment, str) else None

The returned name can be used as the target for commands such as ``pipx inject ENVIRONMENT 'mytool[feature]'``.
pipx records the extra on the main package, so reinstalling the environment retains it.

``pipx run`` may create internal metadata without setting ``environment``, so you have to check the
field value and if the function returns ``None``, show the package's usual installer-neutral advice.
