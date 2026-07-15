###############
 Project scope
###############

pipx installs and runs Python applications. It manages the isolated environments that support those applications and
exposes their entry points on ``PATH``.

*******************
 What pipx manages
*******************

-  Persistent application environments for ``pipx install`` and disposable environments for ``pipx run``.
-  User installations by default and system installations when the caller passes ``--global``.
-  Application dependencies inside a managed environment. For unlocked environments, ``inject`` and ``--preinstall``
   extend an application environment; they do not create standalone library environments.
-  Entry points from the main package and dependencies named with ``--include-resources-from`` or ``--include-deps``.

An install fails when neither the package nor its selected dependencies expose an application. The caller can pass
``--app NAME`` to require an exact entry point. pipx removes a new environment or restores an existing one when the check
fails.

************
 Boundaries
************

pipx does not manage these use cases:

-  standalone environments for importing libraries or modules;
-  tool selection based on the current directory, parent directories, or project metadata;
-  system installation inferred from elevated privileges;
-  a ``pip`` executable from each managed environment on ``PATH``;
-  package search, package ranking, or index-specific application discovery; or
-  frozen pipx executables, operating-system packages, zipapp installers, repositories, and signing keys.

Use ``pipx runpip`` when you need package-manager access inside an environment that pipx created. Distribution projects
may package pipx for their users, but each ecosystem owns its build, release, update, and signing process.

**************************
 Configuration and state
**************************

Ordinary pipx commands do not search the current directory or its parents for configuration. ``pipx manifest sync
PATH`` applies the desired application state from the manifest at ``PATH``; pipx does not infer that path. The manifest
accepts tool state instead of arbitrary command defaults.

pipx can record an environment's resolved dependencies as a lock file in the PyPA ``pylock.toml`` format, so the
environment rebuilds identically; ``pipx manifest lock`` writes these locks and ``pipx install --lock`` reads one back.
pipx does not use ``requirements.txt`` as a state or lock format.

pipx exposes top-level policy when pip and uv honor the same contract. Backend arguments carry controls specific to pip
or uv. ``--cooldown DAYS`` maps one pipx release-age policy to both backends.

Application launchers start the installed application without downloading packages or changing its environment. Health
checks and repairs belong in commands that the user invokes for those purposes.

**************************
 Existing directory lookup
**************************

``pipx run`` has experimental support for applications under ``__pypackages__/<major>.<minor>/lib/bin`` in the current
directory. This behavior predates the scope above and conflicts with the directory-discovery boundary. New features must
not use it as a model; the project should deprecate and remove it in a separate change.

********************
 Choose another tool
********************

Use a project dependency manager such as uv or Poetry for project libraries and development tools. Use ``venv``, pip, or
uv for a library environment. Use a version manager such as mise when a directory must select tool versions, and use the
system package manager to find or install operating-system packages.
