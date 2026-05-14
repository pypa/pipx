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

### Picking a Python interpreter

Pass `--python` to install with a specific Python version. When that Python isn't on your `PATH`, pipx can download a
[python-build-standalone](https://github.com/astral-sh/python-build-standalone) build for you:

```
pipx install --python 3.13 --fetch-python=missing pycowsay
```

Pass `--fetch-python=always` to use a fresh standalone build instead of any system Python. Reach for it when a distro
patched the system Python in ways you can't tolerate. See the [Standalone Python](../how-to/standalone-python.md) how-to
for more options.
