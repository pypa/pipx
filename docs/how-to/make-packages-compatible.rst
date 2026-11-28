##########################
 Make packages compatible
##########################

*********************
 Developing for pipx
*********************

This page shows how to package apps, man pages, and shell completion scripts so that pipx *exposes* them (makes them
available to the user) after:

.. code-block:: console

    $ pipx install MY_PACKAGE

``pipx list`` shows what each installed environment exposes. It reports shell completion scripts from pipx 1.19.0 on.

.. code-block:: console

    $ pipx list

Package apps
============

Declare apps in the ``project.scripts`` table of ``pyproject.toml``, or in the legacy ``setuptools`` ``entry_points``
equivalents in ``setup.cfg`` or ``setup.py``. pipx also exposes ``gui-scripts`` entry points, which are useful for GUI
applications on Windows (they launch without opening a console window).

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

Here ``foo``, ``bar``, and ``baz`` become applications that pipx exposes after installing the package, invoking their
corresponding entry point functions. pipx links or copies the launchers the installer writes into the environment to
``PIPX_BIN_DIR`` (default: ``~/.local/bin``).

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
``my-package`` exists. The `build <https://github.com/pypa/build>`__ package uses this pattern so that ``pipx run
build`` works even though ``build`` names its console script ``pyproject-build``.

.. warning::

    The uv backend hands ``pipx run build`` to ``uv tool run``, which reads console scripts only, so this needs
    ``--backend pip`` there (see :doc:`use-uv-backend`).

Read more about entry points in the `setuptools quickstart
<https://setuptools.pypa.io/en/latest/userguide/quickstart.html#entry-points-and-automatic-script-creation>`__.

Manual pages and shell completions
==================================

pipx also exposes the ``man`` pages and shell completion scripts of a package (completion scripts from pipx 1.16.0 on),
for ``man`` and the shells of UNIX-like systems. Ship them as *data files*, which the installer places under ``share/``
in the package's virtual environment. pipx then links or copies them into ``PIPX_MAN_DIR`` (default:
``~/.local/share/man``), where ``man`` finds them, and ``PIPX_COMPLETION_DIR`` (default: ``~/.local/share``), where the
shell loads them.

.. list-table::
    :header-rows: 1
    :widths: 40 40 20

    - - Shipped by the package
      - Exposed to
      - Used by
    - - ``share/man/man1/`` to ``share/man/man9/``
      - ``~/.local/share/man/man1/`` to ``~/.local/share/man/man9/``
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

    zsh loads the completion scripts only after the user adds the directory to ``fpath`` in ``~/.zshrc`` (see
    :doc:`shell-completions`).

A wheel carries data files in its ``{distribution}-{version}.data/data/`` directory, as defined by the `wheel
distribution format
<https://packaging.python.org/en/latest/specifications/binary-distribution-format/#the-data-directory>`__, and the
installer copies them to the root of the environment. The examples below configure several *build backends* to put
the files there. Each assumes the project's build step writes the data files into a ``generated`` directory laid out
the way they land in the environment:

.. code-block:: text

    generated/
    └── share/
        ├── man/man1/myapp.1
        ├── bash-completion/completions/myapp
        ├── fish/vendor_completions.d/myapp.fish
        └── zsh/site-functions/_myapp

setuptools and hatchling map each source to a destination you name, so they work with any layout. pdm-backend and
uv_build reproduce the source tree inside the environment, so they need this one.

.. tab-set::

    .. tab-item:: setuptools

        .. code-block:: toml

            # pyproject.toml
            [tool.setuptools.data-files]
            "share/man/man1" = ["generated/share/man/man1/*"]
            "share/bash-completion/completions" = ["generated/share/bash-completion/completions/*"]
            "share/fish/vendor_completions.d" = ["generated/share/fish/vendor_completions.d/*"]
            "share/zsh/site-functions" = ["generated/share/zsh/site-functions/*"]

        .. code-block:: ini

            # setup.cfg
            [options.data_files]
            share/man/man1 = generated/share/man/man1/*
            share/bash-completion/completions = generated/share/bash-completion/completions/*
            share/fish/vendor_completions.d = generated/share/fish/vendor_completions.d/*
            share/zsh/site-functions = generated/share/zsh/site-functions/*

        .. code-block:: python

            # setup.py
            setup(
                data_files=[
                    ("share/man/man1", ["generated/share/man/man1/myapp.1"]),
                    ("share/bash-completion/completions", ["generated/share/bash-completion/completions/myapp"]),
                    ("share/fish/vendor_completions.d", ["generated/share/fish/vendor_completions.d/myapp.fish"]),
                    ("share/zsh/site-functions", ["generated/share/zsh/site-functions/_myapp"]),
                ],
            )

        .. note::

            ``setuptools`` needs one entry per destination directory, and no entry can map the whole ``share``
            tree. ``pyproject.toml`` and ``setup.cfg`` entries accept globs; ``setup.py`` lists every file. Keep the
            sources out of ``build``: setuptools leaves its build directory out of the sdist, so a wheel built from
            the sdist would miss them. The `setuptools documentation
            <https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#setuptools-specific-configuration>`__
            calls the ``data-files`` keyword "discouraged", but it has no alternative for files installed outside the
            package tree.

    .. tab-item:: pdm-backend

        .. code-block:: toml

            # pyproject.toml
            [tool.pdm.build]
            source-includes = ["generated/share"]

            [tool.pdm.build.wheel-data]
            data = [
              { path = "generated/share/**/*", relative-to = "generated/" },
            ]

        .. note::

            Each file keeps its path below ``relative-to``, so the source tree must mirror the installed layout.
            Each ``path`` is a file or a glob of files; a bare directory matches nothing. Keep ``relative-to`` on
            every entry, since without it the files land flat in the environment root, where pipx does not look. See
            `PDM-Backend - Wheel data files <https://backend.pdm-project.org/build_config/#wheel-data-files>`__.

    .. tab-item:: uv_build

        .. code-block:: toml

            # pyproject.toml
            [tool.uv.build-backend]
            data = { data = "generated" }

        .. note::

            ``uv_build`` takes the directory *whose contents* it ships, ``generated`` here, so the ``share`` subtree
            lands in the environment. See:

            * `The uv build backend - file inclusion and exclusion
              <https://docs.astral.sh/uv/concepts/build-backend/#file-inclusion-and-exclusion>`__
            * `The uv build backend - the "data" setting
              <https://docs.astral.sh/uv/reference/settings/#build-backend_data>`__

    .. tab-item:: hatchling

        .. code-block:: toml

            # pyproject.toml
            # generated files are usually in .gitignore, which would leave them out of the sdist
            [tool.hatch.build.targets.sdist]
            artifacts = ["generated/share"]

            [tool.hatch.build.targets.wheel.shared-data]
            "generated/share" = "share"

        .. note::

            ``hatchling`` can also map each file to its own destination. See:

            * `hatch - Build configuration <https://hatch.pypa.io/latest/config/build/>`__
            * `hatch - Wheel builder <https://hatch.pypa.io/latest/plugins/builder/wheel/>`__

.. warning::

    ``poetry-core``, the build backend of `Poetry <https://python-poetry.org>`__, does not ship data files (see
    `python-poetry/poetry#8867 <https://github.com/python-poetry/poetry/issues/8867>`__), so a Poetry project can
    expose apps through ``project.scripts`` but not man pages or completion scripts. To ship those, select another
    backend, such as ``hatchling``, in the `build-system table
    <https://python-poetry.org/docs/pyproject/#poetry-and-pep-517>`__.

Detect a pipx installation
==========================

pipx records the environment name in ``pipx_metadata.json`` for packages installed with ``pipx install``. Package code
can read this name when it needs to give pipx-specific recovery instructions:

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

Use the returned name as the target for commands such as ``pipx inject ENVIRONMENT 'mytool[feature]'``. pipx records the
extra on the main package, so reinstalling the environment retains it.

``pipx run`` may create internal metadata without setting ``environment``, so check the field value. Treat other keys as
internal pipx state that may change between versions (see :doc:`../reference/metadata`). If the function returns
``None``, show the package's usual installer-neutral advice.

Check the package
=================

Build the sdist and then a wheel from it, the way installers build from source, and list the wheel's data files. Clear
``dist`` first so the glob matches only the new wheel:

.. code-block:: console

    $ rm -rf dist
    $ pipx run --spec build pyproject-build
    $ python -m zipfile -l dist/*.whl

Every man page and completion script should appear under ``myapp-0.1.data/data/share/``. A file missing there, or
sitting directly under ``data/``, means the backend configuration dropped or flattened it. Then install the wheel,
replacing any earlier install of the package:

.. code-block:: console

    $ pipx install --force dist/*.whl
    $ pipx list
    $ man myapp

``pipx install`` names the exposed apps and man pages, ``pipx list`` shows the completion scripts, and ``man myapp``
opens ``myapp.1``.
