## Getting Started with pipx

This tutorial covers the core pipx workflow: installing an application, running it, and managing it. You need
[pipx installed](../how-to/install-pipx.md) before continuing.

### Install your first application

Pick a small package to try. `pycowsay` works well:

```
pipx install pycowsay
```

pipx creates an isolated virtual environment for `pycowsay`, installs it there, and links the `pycowsay` command into a
directory on your `PATH`. Run it from anywhere:

```
pycowsay "Hello, pipx!"
```

### List installed applications

```
pipx list
```

The output shows the virtual environment location, exposed commands, and the Python version each package uses.

### Run an application without installing

`pipx run` executes an application in a temporary environment and cleans up after itself:

```
pipx run pycowsay moooo!
```

### Upgrade an installed application

```
pipx upgrade pycowsay
```

Or upgrade everything at once:

```
pipx upgrade-all
```

### Uninstall an application

```
pipx uninstall pycowsay
```

pipx deletes the isolated environment and removes the command from your `PATH`.

### Next steps

Continue with the [install applications](install-applications.md) and [run applications](run-applications.md) tutorials
for a closer look at the two core commands. The [how-to guides](../how-to/index.md) cover tasks like injecting packages
and configuring paths. The full [CLI reference](../reference/cli.md) documents every flag.
