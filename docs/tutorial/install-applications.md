## Installing a Package and its Applications

Install an application with:

```
pipx install PACKAGE
```

pipx creates a virtual environment, installs the package, and adds its entry points to a location on your `PATH`.
`pipx install pycowsay` makes the `pycowsay` command available system-wide while sandboxing pycowsay in its own virtual
environment. No `sudo` required. To install for all users on the system, pass `--global` after the subcommand (see
[Configure Paths](../how-to/configure-paths.md#-global-argument)).

```
>> pipx install pycowsay
  installed package pycowsay 2.0.3, Python 3.10.3
  These apps are now globally available
    - pycowsay
done! ✨ 🌟 ✨


>> pipx list
venvs are in /home/user/.local/share/pipx/venvs
apps are exposed on your $PATH at /home/user/.local/bin
   package pycowsay 2.0.3, Python 3.10.3
    - pycowsay


# Now you can run pycowsay from anywhere
>> pycowsay mooo
  ____
< mooo >
  ====
         \
          \
            ^__^
            (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||

```

### Hiding an application

Use `unexpose` when another command with the same name should take precedence without removing the pipx environment.

```
pipx unexpose ansible
```

pipx removes the apps and manual pages recorded for the environment from its global directories. Upgrade and reinstall
operations keep it hidden. Injected apps stay hidden too. Use `expose` to restore the recorded resources.

```
pipx expose ansible
```

### Requiring an application entry point

Pass `--app` when automation depends on a specific command.

```
pipx install --app http httpie
```

pipx checks the exact entry-point name before exposing files. If the package lacks the entry point, installation fails
and pipx removes the new environment. pipx records the name; if a later force install, upgrade, or reinstall drops the
entry point, pipx restores the existing environment.

Use one package spec with `--app`. Repeat the option to require more than one entry point. Dependency entry points
qualify when you also pass `--include-deps`.

### Installing from a lock file

Use a [PEP 751 lock file](https://packaging.python.org/en/latest/specifications/pylock-toml/) when a resolver must
choose the application versions and artifacts. Pass the path; pipx does not search the current directory for a lock.

```
uvx nab lock pyproject.toml
pipx install --lock pylock.toml .
```

[nab](https://pypi.org/project/nab/) resolves the dependencies in `pyproject.toml` and writes `pylock.toml`. pipx runs
the selected backend against the lock. A named package must appear in the lock. For a local project or direct URL, pipx
installs the target without resolving its dependencies. pipx checks the environment before it exposes the application.

pipx records the absolute lock path. `--force` and `reinstall` reuse it; `install-all` imports it. pipx skips the
environment during `upgrade` and `upgrade-all`; update the lock and run `pipx reinstall PACKAGE` to apply it. pipx
rejects `inject` because the added package would fall outside the lock.

`--lock` accepts one package spec. Do not combine it with `--preinstall` or `--upgrade`. Pass `--force --lock` to
replace an installed environment with a new lock. The pip backend requires pip 26.1 or newer; the uv backend requires uv
0.6.15 or newer.

### Keeping an installation within a version range

Use `--upgrade` when you want an installed app to match a package spec:

```
pipx install --upgrade "black>=22,<23"
```

pipx installs the app when it is missing, upgrades or downgrades it when the installed version is outside the requested
range, and does not contact the package index when the installed version already satisfies the spec. Add
`--upgrade-strategy eager` to also upgrade dependencies when the app itself needs to change.

### Picking a Python interpreter

Pass `--python` to install with a specific Python version. When that Python isn't on your `PATH`, pipx can download a
[python-build-standalone](https://github.com/astral-sh/python-build-standalone) build for you:

```
pipx install --python 3.13 --fetch-python=missing pycowsay
```

Pass `--fetch-python=always` to use a fresh standalone build instead of any system Python. Reach for it when a distro
patched the system Python in ways you can't tolerate. See the [Standalone Python](../how-to/standalone-python.md) how-to
for more options.
