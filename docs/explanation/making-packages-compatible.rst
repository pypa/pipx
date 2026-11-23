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

Manual pages
============

To provide documentation via ``man`` pages on UNIX-like systems, ship them as data files. pipx exposes them the same way
it exposes apps.

.. tab-set::

    .. tab-item:: setuptools

        .. code-block:: toml

            # pyproject.toml
            [tool.setuptools.data-files]
            "share/man/man1" = [
              "manpage.1",
            ]

        .. code-block:: ini

            # setup.cfg
            [options.data_files]
            share/man/man1 =
                manpage.1

        .. code-block:: python

            # setup.py
            setup(
                # other arguments here...
                data_files=[("share/man/man1", ["manpage.1"])],
            )

        .. warning::

            The `setuptools documentation
            <https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#setuptools-specific-configuration>`_
            calls the ``data-files`` keyword "discouraged", but it has no alternative when you need to ship ``man``
            pages.

    .. tab-item:: pdm-backend

        .. code-block:: toml

            # pyproject.toml
            [tool.pdm.build]
            source-includes = ["share"]

            [tool.pdm.build.wheel-data]
            data = [
              { path = "share/man/man1/*", relative-to = "." },
            ]

After installing the package, ``man manpage`` opens ``manpage.1``. For a real-world example, see `pycowsay's setup.py
<https://github.com/cs01/pycowsay/blob/master/setup.py>`_.

Shell completions
=================

A package can ship the completion script for its own command the same way it ships a man page. pipx picks up the three
directories a wheel installs completion scripts into and links each one under ``PIPX_COMPLETION_DIR`` (default
``~/.local/share``), so the completions arrive with the package and leave with it.

.. list-table::
    :header-rows: 1
    :widths: 40 40 20

    - - Shipped by the package
      - Exposed to
      - Loaded by
    - - ``share/bash-completion/completions/``
      - ``~/.local/share/bash-completion/completions/``
      - bash
    - - ``share/fish/vendor_completions.d/``
      - ``~/.local/share/fish/vendor_completions.d/``
      - fish
    - - ``share/zsh/site-functions/``
      - ``~/.local/share/zsh/site-functions/``
      - zsh (with the directory on ``fpath``)

Declare them through the data files of your build backend, exactly as with man pages:

.. code-block:: python

    setup(
        name="your-tool",
        data_files=[
            ("share/bash-completion/completions", ["completions/your-tool"]),
            ("share/zsh/site-functions", ["completions/_your-tool"]),
            ("share/fish/vendor_completions.d", ["completions/your-tool.fish"]),
        ],
    )

See :doc:`../how-to/shell-completions` for how each shell loads these directories.

Read more about entry points in the `setuptools quickstart
<https://setuptools.pypa.io/en/latest/userguide/quickstart.html#entry-points-and-automatic-script-creation>`_.

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

