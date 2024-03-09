## How it Works

When installing a package and its binaries on linux (`pipx install package`) pipx will

- create directory `~/.local/share/pipx/venvs/PACKAGE`
- create or reuse a shared virtual environment that contains shared packaging library `pip` in
  `~/.local/share/pipx/shared/`
- ensure the library is updated to its latest version
- create a Virtual Environment in `~/.local/share/pipx/venvs/PACKAGE` that uses the shared pip mentioned above but
  otherwise is isolated (pipx uses a [.pth file](https://docs.python.org/3/library/site.html) to do this)
- install the desired package in the Virtual Environment
- expose binaries at `~/.local/bin` that point to new binaries in `~/.local/share/pipx/venvs/PACKAGE/bin` (such as
  `~/.local/bin/black` -> `~/.local/share/pipx/venvs/black/bin/black`)
- expose manual pages at `~/.local/share/man/man[1-9]` that point to new manual pages in
  `~/.local/pipx/venvs/PACKAGE/share/man/man[1-9]`
- as long as `~/.local/bin/` is on your PATH, you can now invoke the new binaries globally
- on operating systems which have the `man` command, as long as `~/.local/share/man` is a recognized search path of man,
  you can now view the new manual pages globally
- adding `--global` flag to any `pipx` command will execute the action in global scope which will expose app to all
  users - [reference](installation.md#global-installation). Note that this is not available on Windows.

When running a binary (`pipx run BINARY`), pipx will

- create or reuse a shared virtual environment that contains the shared packaging library `pip`
- ensure the library is updated to its latest version
- create a temporary directory (or reuse a cached virtual environment for this package) with a name based on a hash of
  the attributes that make the run reproducible. This includes things like the package name, spec, python version, and
  pip arguments.
- create a Virtual Environment inside it with `python -m venv`
- install the desired package in the Virtual Environment
- invoke the binary

These are all things you can do yourself, but pipx automates them for you. If you are curious as to what pipx is doing
behind the scenes, you can always pass the `--verbose` flag to see every single command and argument being run.

## Developing for pipx

If you are a developer and want to be able to run

```
pipx install MY_PACKAGE
```

make sure you include `scripts` and, optionally for Windows GUI applications `gui-scripts`, sections under your main table[^1] in `pyproject.toml` or their legacy equivalents for `setup.cfg` and `setup.py`.

[^1]: This is often the `[project]` table, but might also be differently named. Read more in the [PyPUG](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#writing-your-pyproject-toml).

=== "pyproject.toml"

    ```ini
    [project.scripts]
    foo = "my_package.some_module:main_func"
    bar = "other_module:some_func"

    [project.gui-scripts]
    baz = "my_package_gui:start_func"

    [tool.setuptools.data-files]
    "share/man/man1" = [ "manpage.1",]
    ```

=== "setup.cfg"

    ```ini
    [options.entry_points]
    console_scripts =
        foo = my_package.some_module:main_func
        bar = other_module:some_func
    gui_scripts =
        baz = my_package_gui:start_func

    [options.data_files]
    share/man/man1 =
        manpage.1
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
        data_files=[('share/man/man1', ['manpage.1'])]
    )
    ```

In this case `foo` and `bar` (and `baz` on Windows) would be available as "applications" to pipx after installing the above example package, invoking their corresponding entry point functions.

If you wish to provide documentation via `man` pages on UNIX-like systems then these can be added via a `data-files` keyword.

In this case the manual page `manpage.1` could be accessed by the user after installing the above example package.

> [!WARNING]
>
> The `data-files` keyword is "discouraged" in the [setuptools documentation](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#setuptools-specific-configuration) but there is no alternative if `man` pages are a requirement.

For a real-world example, see [pycowsay](https://github.com/cs01/pycowsay/blob/master/setup.py)'s `setup.py` source code.

You can read more about entry points [here](https://setuptools.pypa.io/en/latest/userguide/quickstart.html#entry-points-and-automatic-script-creation).
