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
``~/.local/share/pipx/venvs/black``) and installs the package into it. Under the pip backend pipx creates the venv
without pip, then creates or reuses a shared environment that holds an up-to-date ``pip`` and links it into the venv
through a `.pth file <https://docs.python.org/3/library/site.html>`_, so every venv borrows one pip rather than
installing its own. pipx refreshes that shared pip once it is more than 30 days old, or right away when it is older than
pip 26.2.2; ``pipx upgrade-shared`` refreshes it immediately. When pip's files are missing from the shared environment,
pipx rebuilds it before running pip; when a pip command fails because pip no longer imports, pipx rebuilds it and
retries the command once. Under the uv backend there is no shared environment: ``uv venv`` builds the venv (without pip)
and ``uv pip`` installs into it.

Once the package is installed, pipx exposes the application's resources so you can reach them from anywhere. It handles
three kinds:

-  console and GUI scripts, into ``PIPX_BIN_DIR`` (default ``~/.local/bin``), for example
   ``~/.local/bin/black`` -> ``~/.local/share/pipx/venvs/black/bin/black``;
-  manual pages, into ``PIPX_MAN_DIR`` (default ``~/.local/share/man/man[1-9]``);
-  shell completion scripts, into ``PIPX_COMPLETION_DIR`` (default ``~/.local/share``).

pipx symlinks each resource into place. On Windows it copies the file instead when the target directory does not
support symlinks. As long as ``PIPX_BIN_DIR`` is on your ``PATH`` the commands are available globally, and on systems
with ``man`` support the pages are too.

pipx records what it installed and exposed in a per-venv ``pipx_metadata.json`` file. Later commands (``upgrade``,
``reinstall``, ``expose``) read it to reproduce the same state. When an upgrade or reinstall changes the resources a
package ships, pipx exposes the new ones and deletes the links or copies of the ones the package dropped.

Adding ``--global`` to any command targets a system-wide location shared by all users instead of your home directory;
the concrete paths and overrides live in :doc:`../how-to/configure-paths`. It is not available on Windows.

For a ``.py`` script carrying PEP 723 metadata, pipx builds a temporary wheel from the script and its declared
dependencies, installs that wheel like any other package, then records the original path or URL so ``upgrade`` and
``reinstall`` can rebuild it.

.. mermaid::

    flowchart LR
        A["pipx install black"] --> BK{"backend?"}
        BK -- pip --> C["create venv<br/>venvs/black/"]
        BK -- uv --> U["uv venv<br/>(no pip)"]
        C --> P["link shared pip<br/>via .pth"]
        P --> D["install package<br/>pip install / uv pip install"]
        U --> D
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

``pipx run APP`` executes an application without installing it permanently. Under the pip backend pipx either reuses a
cached temporary venv or builds a fresh one, then invokes the app. The cache key is a hash of the requirements (the spec
plus any ``--with`` packages), the ``--python`` value, pip and venv arguments, the backend, and the cooldown; cached
environments expire after 14 days, after which the next run rebuilds against the latest release. The temporary venv
borrows the shared pip.

Under the uv backend pipx usually hands the whole run to ``uv tool run``, which uses uv's own cache. ``pipx run --with
PKG`` adds extra dependencies to the temporary environment either way.

.. mermaid::

    flowchart LR
        A["pipx run pycowsay"] --> BK{"backend?"}
        BK -- pip --> C{"cached<br/>venv?"}
        BK -- uv --> U["uv tool run<br/>(uv's cache)"]
        C -- yes --> E["reuse cached venv"]
        C -- no --> P["python -m venv +<br/>shared pip"]
        P --> D["install pycowsay"]
        D --> F["invoke app"]
        E --> F
        U --> F

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

pipx keeps its venvs and shared libraries under one home directory; the run cache and logs use the platform cache and
log directories unless ``PIPX_HOME`` is set. The tree below is the conceptual shape; the concrete locations, defaults,
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
``py`` launcher when one is on ``PATH``. Outside Windows the launcher is asked only for an ``X`` or ``X.Y`` version, the
only form the Python Launcher for Unix reads as a version request. Only if every step fails, and
``--fetch-python=missing`` is set, does pipx fetch a build from `python-build-standalone
<https://github.com/astral-sh/python-build-standalone>`_.
``--fetch-python=always`` skips these steps and downloads directly. The default, ``--fetch-python=never``, keeps pipx
offline and errors out instead.

For the authoritative step-by-step order, the ``--fetch-python`` values, and when a downloaded build beats a patched
system Python, see :doc:`../how-to/standalone-python`.

.. mermaid::

    flowchart TD
        S["--python VALUE"] --> AL{"--fetch-python<br/>=always?"}
        AL -- yes --> DL["download standalone build"]
        AL -- no --> A{"file exists?"}
        A -- yes --> USE["use interpreter"]
        A -- no --> B{"on PATH?<br/>shutil.which"}
        B -- yes --> USE
        B -- no --> C{"pythonX.Y?<br/>(non-Windows)"}
        C -- yes --> USE
        C -- no --> D{"py launcher?"}
        D -- yes --> USE
        D -- no --> E{"--fetch-python<br/>=missing?"}
        E -- "yes" --> DL
        E -- "no (never, default)" --> ERR["error"]

        classDef input fill:#3f72af,stroke:#28517f,color:#fff
        classDef decision fill:#c78c20,stroke:#8a6011,color:#fff
        classDef out fill:#388e3c,stroke:#256128,color:#fff
        classDef err fill:#b3261e,stroke:#7a1a15,color:#fff
        class S input
        class AL,A,B,C,D,E decision
        class USE,DL out
        class ERR err
