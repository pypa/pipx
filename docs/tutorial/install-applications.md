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
