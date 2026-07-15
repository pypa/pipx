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

### Selecting applications from dependencies

`--include-deps` exposes apps and manual pages from every dependency. Use `--include-resources-from` to expose resources from
one dependency:

```
pipx install "nox[tox_to_nox]" --include-resources-from tox
```

Repeat `--include-resources-from` to select more dependencies. pipx records the selection for upgrade and reinstall. The
install fails and rolls back when a selected package is not a dependency with apps or manual pages.

### Running an application without exposing it

Use `exec` to run a recorded application from an existing environment without adding it to the pipx binary directory.

```
pipx inject nox tox
pipx exec nox tox --version
```

The application may belong to the main package, an injected package, or a dependency. pipx adds the selected
environment's binary directory to the child process `PATH` and sets `VIRTUAL_ENV`, so sibling applications can call each
other. `exec` does not install packages, change the environment, expose applications, or start a shell. Use `inject`
first when the environment does not contain the application.

### Requiring an application entry point

Pass `--app` when automation depends on a specific command.

```
pipx install --app http httpie
```

pipx checks the exact entry-point name before exposing files. If the package lacks the entry point, installation fails
and pipx removes the new environment. pipx records the name; if a later force install, upgrade, or reinstall drops the
entry point, pipx restores the existing environment.

Use one package spec with `--app`. Repeat the option to require more than one entry point. `--include-resources-from` can
select dependency entry points; `--include-deps` selects all dependency entry points.

### Installing a PEP 723 script

Install a local script with
[PEP 723 inline metadata](https://packaging.python.org/en/latest/specifications/inline-script-metadata/) when it should
remain available instead of using a temporary `pipx run` environment:

```
pipx install ./hello.py
```

pipx uses the filename without `.py` as the application and environment name. Pass `--app` to choose another name:

```
pipx install --app greet ./hello.py
```

The script must contain a `# /// script` metadata block. pipx installs its declared dependencies and exposes the script
through the same metadata and environment lifecycle as a package. `list`, `uninstall`, `inject`, `reinstall`, and
`upgrade` therefore work without script-specific commands. Reinstall and upgrade read the source again.

HTTP and HTTPS script URLs work too. Treat a mutable URL like any other unpinned source. To make dependency artifacts
reproducible, pass an explicit `pylock.toml` with `--lock`; pipx installs the locked environment before installing the
script without dependency resolution.

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
0.9.17 or newer.

### Delaying new releases

Use a cooldown when you want time to review a release before installing it:

```
pipx install --cooldown 7 PACKAGE
```

`--cooldown DAYS` excludes remote-index artifacts uploaded within that many days. pipx stores the value for each
installed or injected package; upgrades and rebuilds reuse it. A command-line value overrides the stored value. Pass
`--cooldown 0` to clear the restriction. An `install-all` override does not alter a locked environment.

`pipx run --cooldown DAYS` applies the same policy to temporary environments and keeps caches for different cooldowns
separate. The pip backend uses `--uploaded-prior-to`; the uv backend uses `--exclude-newer`. Relative cooldowns require
pip 26.1 or uv 0.9.17. The package index must publish artifact upload times. The cooldown does not apply to local paths,
VCS URLs, or `--find-links` artifacts.

A cooldown delays security releases. Use vulnerability scanning and pass `--cooldown 0` to install an urgent fix without
delay.

### Applying a tool manifest

Use an explicit manifest to manage a set of pipx tools:

```toml
[project]
name = "pipx-tools"
version = "1"
dependencies = []
requires-python = ">=3.10"

[dependency-groups]
black = ["black>=25,<26"]
httpie = ["httpie"]

[tool.pipx]
version = "1.0"

[tool.pipx.tools.black]
apps = ["black"]
lock = "pylock.black.toml"

[tool.pipx.tools.httpie]
apps = ["http", "https"]
```

Each dependency group contains one package requirement and names its pipx environment. Keep `project.dependencies` empty
so each group resolves independently. Add a matching `tool.pipx.tools` table only when the tool needs policy beyond its
package requirement.

Use the normalized package name plus its suffix as the environment name:

```toml
[dependency-groups]
black-24 = ["black==24.10.0"]

[tool.pipx.tools.black-24]
suffix = "-24"
apps = ["black"]
```

Package requirements use PEP 508 syntax without environment markers. A tool table may set `suffix`, `apps`,
`include-dependencies`, `include-resources-from`, `expose`, or `lock`. Use `include-resources-from = ["PACKAGE"]` to select
dependency resources; do not combine it with `include-dependencies`. Relative lock paths start from the manifest
directory. Put nab settings in `tool.nab`.

Install [nab](https://pypi.org/project/nab/), generate the declared locks, and apply the manifest:

```console
pipx install nab
pipx lock ./pipx.toml
pipx sync ./pipx.toml
```

`pipx lock` passes the manifest to nab once per locked dependency group. Existing locks seed their replacements, and
pipx replaces the declared files only after every resolution succeeds. Entries without `lock` remain unlocked.

`pipx sync` installs, upgrades, or downgrades each declared tool. The backend resolves unlocked package specs on each
run; pipx installs locked entries from the artifacts in their named PEP 751 files. pipx restores an existing environment
and its exposed resources when a tool fails to install or lacks a required app.

Pass `--prune` to uninstall environments absent from the manifest. Without it, sync leaves other pipx environments
alone. Pass `--global` or `--backend` after `sync` to select the pipx store or installation backend. pipx reads only the
manifest path supplied on the command line.

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
