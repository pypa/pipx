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

### Keeping an installation within a version range

Use `--upgrade` when you want an installed app to match a package spec:

```
pipx install --upgrade "black>=22,<23"
```

pipx installs the app when it is missing, upgrades or downgrades it when the installed version is outside the requested
range, and does not contact the package index when the installed version already satisfies the spec. Add
`--upgrade-strategy eager` to also upgrade dependencies when the app itself needs to change.

### Reconciling an installation for automation

Use `--exact` when a script owns both the package request and its environment settings:

```
pipx install --exact --python /usr/local/bin/python3.12 "black==25.1.0"
```

pipx installs a missing package, checks mutable package specs for upgrades, and rebuilds the environment when settings
differ from the request. If a rebuild fails, pipx restores the previous environment. Install options describe the
desired state. Omitted options use defaults from the current pipx configuration and discard values an earlier install
recorded. pipx retains injected packages as separate state.

`--exact` does not accept `--preinstall` because pipx does not record preinstalled packages and cannot compare their
requested state.

### Picking a Python interpreter

Pass `--python` to install with a specific Python version. When that Python isn't on your `PATH`, pipx can download a
[python-build-standalone](https://github.com/astral-sh/python-build-standalone) build for you:

```
pipx install --python 3.13 --fetch-python=missing pycowsay
```

Pass `--fetch-python=always` to use a fresh standalone build instead of any system Python. Reach for it when a distro
patched the system Python in ways you can't tolerate. See the [Standalone Python](../how-to/standalone-python.md) how-to
for more options.
