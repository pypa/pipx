## Developing for pipx

If you are a developer and want to be able to run

```
pipx install MY_PACKAGE
```

make sure you include `scripts` in your main table[^1] in `pyproject.toml` or its legacy equivalents for `setup.cfg` and
`setup.py`. pipx also exposes `gui-scripts` entry points, which are useful for GUI applications on Windows (they launch
without opening a console window).

=== "pyproject.toml"

    ```ini
    [project.scripts]
    foo = "my_package.some_module:main_func"
    bar = "other_module:some_func"

    [project.gui-scripts]
    baz = "my_package_gui:start_func"
    ```

=== "setup.cfg"

    ```ini
    [options.entry_points]
    console_scripts =
        foo = my_package.some_module:main_func
        bar = other_module:some_func
    gui_scripts =
        baz = my_package_gui:start_func
    ```

=== "setup.py"

    ```python
    setup(
        # other arguments here...
        entry_points={
            'console_scripts': [
                'foo = my_package.some_module:main_func',
                'bar = other_module:some_func',
            ],
            'gui_scripts': [
                'baz = my_package_gui:start_func',
            ]
        },
    )
    ```

In this case `foo` and `bar` (and `baz` on Windows) would be available as "applications" to pipx after installing the
above example package, invoking their corresponding entry point functions.

```mermaid
flowchart LR
    TOML["pyproject.toml<br/>[project.scripts]"] --> |"defines"| EP["entry points<br/>foo, bar"]
    EP --> |"pipx install"| VENV["isolated venv"]
    VENV --> |"symlinks"| BIN["~/.local/bin/<br/>foo, bar"]
    BIN --> |"invokes"| FUNC["my_package:<br/>main_func()"]

    style TOML fill:#3f72af,color:#fff
    style EP fill:#2a9d8f,color:#fff
    style VENV fill:#7c4dff,color:#fff
    style BIN fill:#388e3c,color:#fff
    style FUNC fill:#c78c20,color:#fff
```

### The `pipx.run` entry point group

When a user runs `pipx run PACKAGE`, pipx looks for a console script matching the package name. If the package name and
script name differ, the user has to write `pipx run --spec PACKAGE SCRIPT`, which is less convenient.

Package authors can declare a `pipx.run` entry point group to tell pipx which function to invoke for `pipx run`. This
entry point takes priority over console scripts when present.

=== "pyproject.toml"

    ```toml
    [project.entry-points."pipx.run"]
    my-package = "my_package.cli:main"
    ```

=== "setup.cfg"

    ```ini
    [options.entry_points]
    pipx.run =
        my-package = my_package.cli:main
    ```

With this declaration, `pipx run my-package` invokes `my_package.cli:main` even if no console script named `my-package`
exists. The [build](https://github.com/pypa/build) package uses this pattern so that `pipx run build` works even though
build's console script is named `pyproject-build`.

### Manual pages

If you wish to provide documentation via `man` pages on UNIX-like systems then these can be added as data files:

=== "setuptools"

    ```toml title="pyproject.toml"
    [tool.setuptools.data-files]
    "share/man/man1" = [
      "manpage.1",
    ]
    ```

    ```ini title="setup.cfg"
    [options.data_files]
    share/man/man1 =
        manpage.1
    ```

    ```python title="setup.py"
    setup(
        # other arguments here...
        data_files=[('share/man/man1', ['manpage.1'])]
    )
    ```

    > [!WARNING]
    > The `data-files` keyword is "discouraged" in the
    > [setuptools documentation](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#setuptools-specific-configuration)
    > but there is no alternative if `man` pages are a requirement.

=== "pdm-backend"

    ```toml title="pyproject.toml"
    [tool.pdm.build]
    source-includes = ["share"]

    [tool.pdm.build.wheel-data]
    data = [
      { path = "share/man/man1/*", relative-to = "." },
    ]
    ```

In this case the manual page `manpage.1` could be accessed by the user after installing the above example package.

For a real-world example, see [pycowsay](https://github.com/cs01/pycowsay/blob/master/setup.py)'s `setup.py` source
code.

You can read more about entry points
[here](https://setuptools.pypa.io/en/latest/userguide/quickstart.html#entry-points-and-automatic-script-creation).

[^1]: This is often the `[project]` table, but might also be differently named. Read more in the
    [PyPUG](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#writing-your-pyproject-toml).
