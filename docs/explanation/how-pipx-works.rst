################
 How pipx works
################

.. note::

    This page describes the **pip backend** model, where a shared ``pip`` environment backs every managed venv through a
    ``.pth`` file. When the **uv backend** is active (the default whenever uv is available, via the ``pipx[uv]`` extra
    or on ``PATH``) pipx skips the shared environment and uses ``uv venv`` and ``uv pip`` instead; uv-created venvs ship
    without pip. See :doc:`../how-to/use-uv-backend`.

***************************
 Installing an application
***************************

``pipx install PACKAGE`` creates an isolated virtual environment under ``PIPX_HOME`` (for example
``~/.local/share/pipx/venvs/black``) and installs the package into it. Under the pip backend pipx first creates or
reuses a shared environment that holds an up-to-date ``pip`` and exposes it to each managed venv through a
`.pth file <https://docs.python.org/3/library/site.html>`_, so every venv borrows one pip rather than installing its
own. Under the uv backend there is no shared environment: ``uv venv`` builds the venv (without pip) and ``uv pip``
installs into it.

Once the package is installed, pipx exposes the application's resources so you can reach them from anywhere. It handles
four kinds:

-  console and GUI scripts, into ``PIPX_BIN_DIR`` (default ``~/.local/bin``), for example
   ``~/.local/bin/black`` -> ``~/.local/share/pipx/venvs/black/bin/black``;
-  manual pages, into ``PIPX_MAN_DIR`` (default ``~/.local/share/man/man[1-9]``);
-  shell completion scripts, into ``PIPX_COMPLETION_DIR`` (default ``~/.local/share``).

pipx symlinks each resource into place. On Windows, and on any filesystem that does not support symlinks, it copies the
file instead. As long as ``PIPX_BIN_DIR`` is on your ``PATH`` the commands are available globally, and on systems with
``man`` support the pages are too.

pipx records what it installed and exposed in a per-venv ``pipx_metadata.json`` file. Later commands (``upgrade``,
``reinstall``, ``expose``) read it to reproduce the same state.

Adding ``--global`` to any command targets a system-wide location shared by all users instead of your home directory;
the concrete paths and overrides live in :doc:`../how-to/configure-paths`. It is not available on Windows.

For a ``.py`` script carrying PEP 723 metadata, pipx builds a temporary wheel from the script and its declared
dependencies, installs that wheel like any other package, then records the original path or URL so ``upgrade`` and
``reinstall`` can rebuild it.

.. mermaid::

    flowchart LR
        A["pipx install black"] --> BK{"backend?"}
        BK -- pip --> P["shared venv (pip)<br/>reused via .pth"]
        BK -- uv --> U["uv venv<br/>(no pip)"]
        P --> C["create venv<br/>venvs/black/"]
        U --> C
        C --> D["install package<br/>pip install / uv pip install"]
        D --> E["expose apps<br/>~/.local/bin"]
        D --> F["expose man pages<br/>~/.local/share/man"]
        D --> G["expose completions<br/>PIPX_COMPLETION_DIR"]

        classDef input fill:#3f72af,stroke:#28517f,color:#fff
        classDef decision fill:#c78c20,stroke:#8a6011,color:#fff
        classDef proc fill:#2a9d8f,stroke:#1c6b61,color:#fff
        classDef out fill:#388e3c,stroke:#256128,color:#fff
        class A input
        class BK decision
        class P,U,C,D proc
        class E,F,G out

*************************
 Running an application
*************************

``pipx run APP`` executes an application without installing it permanently. pipx either reuses a cached temporary venv
or builds a fresh one, then invokes the app. The cache key is a hash of the package name, spec, Python version, and pip
arguments; cached environments expire after 14 days, after which the next run rebuilds against the latest release.

Under the pip backend the temporary venv borrows the shared pip; under the uv backend uv creates and populates it.
``pipx run --with PKG`` adds extra dependencies to that temporary environment.

.. mermaid::

    flowchart LR
        A["pipx run pycowsay"] --> C{"cached<br/>venv?"}
        C -- yes --> E["reuse cached venv"]
        C -- no --> BK{"backend?"}
        BK -- pip --> P["shared pip +<br/>python -m venv"]
        BK -- uv --> U["uv venv + uv pip"]
        P --> D["install pycowsay"]
        U --> D
        D --> F["invoke app"]
        E --> F

        classDef input fill:#3f72af,stroke:#28517f,color:#fff
        classDef decision fill:#c78c20,stroke:#8a6011,color:#fff
        classDef proc fill:#2a9d8f,stroke:#1c6b61,color:#fff
        classDef out fill:#388e3c,stroke:#256128,color:#fff
        class A input
        class C,BK decision
        class P,U,D,E proc
        class F out

**********************
 Exposing apps on PATH
**********************

When you type an exposed command, the shell finds the symlink (or copy) in ``PIPX_BIN_DIR`` and follows it to the
launcher inside the app's venv. That launcher runs the venv's own Python against the installed package, so the app
always uses its isolated dependencies and never your system site-packages.

.. mermaid::

    flowchart LR
        U["user types<br/>black"] --> B["~/.local/bin/black<br/>(symlink or copy)"]
        B --> V["venvs/black/bin/black<br/>(launcher)"]
        V --> P["venv Python<br/>+ installed black"]

        classDef input fill:#3f72af,stroke:#28517f,color:#fff
        classDef proc fill:#2a9d8f,stroke:#1c6b61,color:#fff
        classDef out fill:#388e3c,stroke:#256128,color:#fff
        class U input
        class B,V proc
        class P out

******************
 Directory layout
******************

pipx keeps its state under one home directory. The tree below is the conceptual shape; the concrete locations, defaults,
and every override live in :doc:`../how-to/configure-paths`.

.. mermaid::

    flowchart TD
        HOME["~"] --> BIN["~/.local/bin/<br/>(on PATH)"]
        HOME --> DATA["~/.local/share/pipx/"]
        DATA --> SHARED["shared/<br/>(pip, pip backend only)"]
        DATA --> VENVS["venvs/"]
        VENVS --> V1["black/"]
        VENVS --> V2["poetry/"]
        VENVS --> V3["ruff/"]
        V1 --> V1BIN["bin/black"]
        BIN -->|symlink or copy| V1BIN

        classDef input fill:#3f72af,stroke:#28517f,color:#fff
        classDef proc fill:#2a9d8f,stroke:#1c6b61,color:#fff
        classDef out fill:#388e3c,stroke:#256128,color:#fff
        classDef venv fill:#7c4dff,stroke:#5a2fd0,color:#fff
        classDef shared fill:#c78c20,stroke:#8a6011,color:#fff
        class HOME input
        class DATA,VENVS proc
        class BIN out
        class SHARED shared
        class V1,V2,V3,V1BIN venv

You can do all of this yourself; pipx automates it. Pass ``--verbose`` to see each command it runs and to stream
installer output.

***********************************
 Resolving the Python interpreter
***********************************

pipx prefers a real system Python and only downloads a standalone build as a fallback. When you pass ``--python``, it
tries the value as a literal path, then as a command on ``PATH``, then as a ``pythonX.Y`` command, then through the
``py`` launcher on Windows. Only if every step fails, and ``--fetch-python`` permits it, does pipx fetch a build from
`python-build-standalone <https://github.com/astral-sh/python-build-standalone>`_. The default, ``--fetch-python=never``,
keeps pipx offline and errors out instead.

For the authoritative step-by-step order, the ``--fetch-python`` values, and when a downloaded build beats a patched
system Python, see :doc:`../how-to/standalone-python`.

.. mermaid::

    flowchart TD
        S["--python VALUE"] --> A{"file exists?"}
        A -- yes --> USE["use interpreter"]
        A -- no --> B{"on PATH?<br/>shutil.which"}
        B -- yes --> USE
        B -- no --> C{"pythonX.Y?<br/>(non-Windows)"}
        C -- yes --> USE
        C -- no --> D{"py launcher?<br/>(Windows)"}
        D -- yes --> USE
        D -- no --> E{"--fetch-python<br/>allows download?"}
        E -- "missing / always" --> DL["download standalone build"]
        E -- "never (default)" --> ERR["error"]

        classDef input fill:#3f72af,stroke:#28517f,color:#fff
        classDef decision fill:#c78c20,stroke:#8a6011,color:#fff
        classDef out fill:#388e3c,stroke:#256128,color:#fff
        classDef err fill:#b3261e,stroke:#7a1a15,color:#fff
        class S input
        class A,B,C,D,E decision
        class USE,DL out
        class ERR err
