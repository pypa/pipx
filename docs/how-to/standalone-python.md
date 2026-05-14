## Use a Standalone Python Build

pipx can install applications under a Python interpreter downloaded from
[python-build-standalone](https://github.com/astral-sh/python-build-standalone) instead of the system Python. Reach for
this when the system Python is missing the version you asked for, or when the distro patched its Python in ways that
break the application.

### Choosing when to download

Set `--fetch-python` (or `PIPX_FETCH_PYTHON`) to one of three values:

| Value     | Behaviour                                                                          |
| --------- | ---------------------------------------------------------------------------------- |
| `never`   | Default. Don't download. Use Python interpreters from `PATH` or the `py` launcher. |
| `missing` | Look for the requested version locally first; download it when it isn't there.     |
| `always`  | Skip the local search and use a standalone build for the requested version.        |

```
# Download only when the requested version is missing locally
pipx install --python 3.13 --fetch-python=missing my-package

# Use a fresh standalone build, ignoring system Python
pipx install --python 3.13 --fetch-python=always my-package

# Set the policy for your shell session
export PIPX_FETCH_PYTHON=missing
pipx install --python 3.13 my-package
```

pipx unpacks the interpreter into its standalone cache. Manage cached interpreters with `pipx interpreter list`,
`pipx interpreter prune`, and `pipx interpreter upgrade` (see the [reference](../reference/examples.md)).

### When `--fetch-python=always` is the right choice

- CI runs where you don't want to depend on the runner's preinstalled Python.
- Distros that strip optional modules (`tkinter`, `lzma`) from their packaged Python.
- Air-gapped boxes where you have populated the standalone cache and want pipx to ignore the system Python.

### Migrating from `--fetch-missing-python`

`--fetch-missing-python` and `PIPX_FETCH_MISSING_PYTHON` still work, but pipx warns and treats them as deprecated. They
behave like `--fetch-python=missing` / `PIPX_FETCH_PYTHON=missing`. pipx errors out if you set both
`PIPX_FETCH_MISSING_PYTHON` and `PIPX_FETCH_PYTHON`.
