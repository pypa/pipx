## How it Works

### `pipx install`

When installing a package and its binaries on Linux (`pipx install package`), pipx first creates or reuses a shared
virtual environment at `~/.local/share/pipx/shared/` that contains the packaging library `pip`, ensuring it is updated
to its latest version. It then creates an isolated virtual environment at `~/.local/share/pipx/venvs/PACKAGE` that uses
the shared pip via a [.pth file](https://docs.python.org/3/library/site.html) and installs the desired package into it.

Once the package is installed, pipx exposes its console scripts and GUI scripts by symlinking them into `~/.local/bin`
(for example, `~/.local/bin/black` -> `~/.local/share/pipx/venvs/black/bin/black`). It also symlinks any manual pages
into
`~/.local/share/man/man[1-9]`. As long as `~/.local/bin/` is on your `PATH`, the new commands are available globally,
and on systems with `man` support the pages are accessible too.

Adding the `--global` flag to any `pipx` command executes the action in global scope, exposing the app to all system
users. See the [configuration reference](../how-to/configure-paths.md#-global-argument) for details. Note that this is
not available on Windows.

```mermaid
flowchart LR
    A["pipx install black"] --> B["shared venv<br/>(pip)"]
    B --> C["create venv<br/>~/.local/share/pipx/<br/>venvs/black/"]
    C --> D["pip install black"]
    D --> E["symlink binaries<br/>~/.local/bin/black"]
    D --> F["symlink man pages<br/>~/.local/share/man/"]

    style A fill:#3f72af,color:#fff
    style B fill:#2a9d8f,color:#fff
    style C fill:#2a9d8f,color:#fff
    style D fill:#2a9d8f,color:#fff
    style E fill:#388e3c,color:#fff
    style F fill:#388e3c,color:#fff
```

### `pipx run`

`pipx run BINARY` reuses the same shared pip environment, then either reuses a cached virtual environment or creates a
new temporary one. The cache key is a hash of the package name, spec, python version, and pip arguments. pipx creates a
virtual environment with `python -m venv`, installs the package, and invokes the binary.

Cached environments expire after a few days. On next run, pipx fetches the latest version.

```mermaid
flowchart LR
    A["pipx run pycowsay"] --> B["shared venv<br/>(pip)"]
    B --> C{"cached<br/>venv?"}
    C -- "yes" --> E["reuse cached venv"]
    C -- "no" --> D["create temp venv<br/>pip install pycowsay"]
    D --> F["invoke binary"]
    E --> F

    style A fill:#3f72af,color:#fff
    style B fill:#2a9d8f,color:#fff
    style C fill:#c78c20,color:#fff
    style D fill:#2a9d8f,color:#fff
    style E fill:#2a9d8f,color:#fff
    style F fill:#388e3c,color:#fff
```

### Directory layout

The overall directory structure that pipx manages looks like this:

```mermaid
flowchart TD
    HOME["~"] --> BIN["~/.local/bin/<br/>(on PATH)"]
    HOME --> DATA["~/.local/share/pipx/"]
    DATA --> SHARED["shared/<br/>(pip, setuptools)"]
    DATA --> VENVS["venvs/"]
    VENVS --> V1["black/"]
    VENVS --> V2["poetry/"]
    VENVS --> V3["ruff/"]
    V1 --> V1BIN["bin/black"]
    BIN --> |"symlink"| V1BIN

    style HOME fill:#3f72af,color:#fff
    style BIN fill:#388e3c,color:#fff
    style DATA fill:#2a9d8f,color:#fff
    style SHARED fill:#c78c20,color:#fff
    style VENVS fill:#2a9d8f,color:#fff
    style V1 fill:#7c4dff,color:#fff
    style V2 fill:#7c4dff,color:#fff
    style V3 fill:#7c4dff,color:#fff
    style V1BIN fill:#7c4dff,color:#fff
```

You can do all of this yourself. pipx automates it. Pass `--verbose` to see every command and argument pipx runs.
