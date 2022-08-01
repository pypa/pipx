## How it Works

When installing a package and its binaries (`pipx install package`) pipx will

- create directory `~/.local/pipx/venvs/PACKAGE`
- create or re-use a shared virtual environment that contains shared packaging libraries `pip`, `setuptools` and `wheel` in `~/.local/pipx/shared/`
- ensure all packaging libraries are updated to their latest versions
- create a Virtual Environment in `~/.local/pipx/venvs/PACKAGE` that uses the shared pip mentioned above but otherwise is isolated (pipx uses a [.pth file]( https://docs.python.org/3/library/site.html) to do this)
- install the desired package in the Virtual Environment
- expose binaries at `~/.local/bin` that point to new binaries in `~/.local/pipx/venvs/PACKAGE/bin` (such as `~/.local/bin/black` -> `~/.local/pipx/venvs/black/bin/black`)
- As long as `~/.local/bin/` is on your PATH, you can now invoke the new binaries globally

When running a binary (`pipx run BINARY`), pipx will

- create or re-use a shared virtual environment that contains shared packaging libraries `pip`, `setuptools` and `wheel` in `~/.local/pipx/shared/`
- ensure all packaging libraries are updated to their latest versions
- create a temporary directory (or reuse a cached virtual environment for this package) with a name based on a hash of the attributes that make the run reproducible. This includes things like the package name, spec, python version, and pip arguments.
- create a Virtual Environment inside it with `python -m venv`
- install the desired package in the Virtual Environment
- invoke the binary

These are all things you can do yourself, but pipx automates them for you. If you are curious as to what pipx is doing behind the scenes, you can always pass the `--verbose` flag to see every single command and argument being run.

## Developing for pipx

If you are a developer and want to be able to run
```
pipx install MY_PACKAGE
```

make sure you include an `entry_points` section in your `setup.py` file.
```
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
    }
)
```

In this case `main_func` and `some_func` would be available to pipx after installing the above example package.

For a real-world example, see [pycowsay](https://github.com/cs01/pycowsay/blob/master/setup.py)'s `setup.py` source code.

You can read more about entry points [here](https://setuptools.pypa.io/en/latest/userguide/quickstart.html#entry-points-and-automatic-script-creation).
