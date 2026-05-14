## Inject a package

`pipx inject` adds extra packages into an existing pipx-managed virtual environment. If you have `ipython` installed and
want `matplotlib` available inside it:

```
pipx inject ipython matplotlib
```

Inject multiple packages at once, from a requirements file, or both:

```
pipx inject ipython matplotlib pandas
pipx inject ipython -r useful-packages.txt
pipx inject ipython extra-pkg -r more-packages.txt
```

### Expose injected apps

By default, injected packages do not add their entry points to your `PATH`. Use `--include-apps` to expose them:

```
pipx inject ipython black --include-apps
```

`--include-deps` exposes entry points from the injected package's dependencies too (implies `--include-apps`).

### Other flags

- `--force` / `-f` reinstalls the package even if it is already injected.
- `--editable` / `-e` installs the package in editable (development) mode.
- `--with-suffix SUFFIX` targets a suffixed venv (e.g. `ipython_3.11`).
- `--pip-args` passes extra arguments to pip (e.g. `--pip-args='--no-cache-dir'`).
- `--index-url` / `-i` sets the PyPI index URL for this inject.
- `--system-site-packages` gives the venv access to the system site-packages.
