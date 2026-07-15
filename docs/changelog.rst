###########
 Changelog
###########

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_, and this project adheres to
`Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

This project uses `towncrier <https://towncrier.readthedocs.io/>`_ for keeping the changelog. DO NOT commit any changes
to this file.

.. towncrier-draft-entries:: Unreleased

.. towncrier release notes start

`1.16.0 <https://github.com/pypa/pipx/tree/1.16.0>`_ - 2026-07-15
=================================================================

Features
--------

- Add `pipx list --outdated` and JSON output. (:issue:`149`)
- Honour the `requires-python` a package declares. When the default interpreter fails it, pipx looks for one on the system
  that satisfies it and builds the environment there, so `pipx install mytool` no longer needs the user to work out the
  right `--python`. Pass `--fetch-python=missing` to let pipx download a matching interpreter when the system carries
  none, and name `--python` yourself to keep the last word. (:issue:`387`)
- Normalize inferred `pipx run` package names. (:issue:`618`)
- Allow `pipx list` to select installed packages by name. (:issue:`640`)
- Add `--output` to structured commands. (:issue:`828`)
- Freeze the structured result envelope at `pipx_result_version` 1. Every `--output json` document now carries the command
  as a list of CLI tokens, a `status` of `success`, `partial`, or `error`, the process `exit_code`, the command `data`,
  and a top-level `errors` list whose entries each have a stable `code` and `message` alongside the `environment` and
  `package` they concern. A failure that stops a command before it builds a result renders the same envelope. (:issue:`828`)
- Add quiet and JSON output for package maintenance. (:issue:`828`)
- Give `pipx reinstall` and `pipx reinstall-all` the structured output the other commands carry. They printed straight to
  the terminal, so `--quiet` left `uninstalled NAME!` behind and no `--output json` existed to read the result from a
  script. Both now report through the shared renderer. (:issue:`828`)
- Give `pipx cache`, `pipx interpreter`, `pipx upgrade-shared`, `pipx manifest lock` and `pipx manifest sync` the
  structured output the other commands carry, so `--quiet` silences them and `--output json` hands a script the result.
  The `cache` and `interpreter` subcommands take `--quiet` and `--verbose` for the first time, since the shared options
  had passed them by. `pipx ensurepath` goes on printing its guidance, because its job is to tell a person what to add to
  a shell profile. (:issue:`828`)
- Add `--output json` to `pipx inject` and `pipx uninject`. (:issue:`828`)
- Infer the app name when running packages from VCS URLs. (:issue:`854`)
- Stream installer output during verbose installs. (:issue:`1069`)
- Draw the download progress bar of `pip` and `uv` during a plain `pipx install`, in place of the pipx spinner. pipx hands
  the installer a pseudo-terminal, which is the only way `uv` reports progress, and asks `uv` for its default output
  rather than the quiet one. A redirected stream keeps the previous behaviour. (:issue:`1069`)
- Allow commands to skip shared-library maintenance. (:issue:`1278`)
- Install PEP 723 scripts as persistent applications. (:issue:`1388`)
- Point library install errors to `inject` and `--preinstall`. (:issue:`1411`)
- Add commands to diagnose and repair broken environment interpreters. (:issue:`1442`)
- Add explicit tool manifests with separate PEP 751 locks. (:issue:`1506`)
- Add `pipx install --upgrade` to reconcile apps with package specs. (:issue:`1572`)
- Expose the shell completion scripts a package ships, the way pipx already exposes its man pages. A wheel that installs
  into `share/bash-completion/completions`, `share/zsh/site-functions` or `share/fish/vendor_completions.d` gets those
  files linked under `PIPX_COMPLETION_DIR`, which defaults to `~/.local/share`. `bash` and `fish` read those locations on
  their own; `zsh` needs the site-functions directory on its `fpath`. Uninstalling the package takes the links away. (:issue:`1604`)
- Add `pipx reset`, which uninstalls every pipx-managed package and removes the shared libraries, the caches, the
  standalone interpreters, the logs and the trash, so pipx starts over from a fresh install. It asks before it removes
  anything, `--yes` answers for a script, and `--dry-run` lists what would go. (:issue:`1606`)
- Add Python interpreter arguments to `pipx run`. (:issue:`1613`)
- Add commands to hide and restore resources exposed from an environment. (:issue:`1645`)
- Install the generated pipx manual page from wheels. (:issue:`1657`)
- Add `pipx cache` and `pipx run --refresh`. (:issue:`1681`)
- Add `--include-apps-from` for selected dependencies. (:issue:`1725`)
- Add `pipx exec ENVIRONMENT APPLICATION` for installed environments. (:issue:`1726`)
- Support injecting extras into a main package. (:issue:`1805`)
- Install from PEP 751 lock files. (:issue:`1807`)
- Add dependency cooldowns. (:issue:`1811`)
- Validate requested apps and restore prior environments on failure. (:issue:`1908`)
- Default `PIPX_HOME` to the platform data directory on macOS and Windows again, which restores
  `~/Library/Application Support/pipx` on macOS. `platformdirs` reads `XDG_DATA_HOME` and `XDG_CACHE_HOME` on macOS, so
  exporting those moves the pipx directories. A pipx home from an earlier release keeps working as a fallback. (:issue:`1946`)
- Group the manifest commands under `pipx manifest`: use `pipx manifest lock` and `pipx manifest sync` in place of the
  top-level `pipx lock` and `pipx sync`. Keeping both verbs under one noun matches `pipx cache` and `pipx interpreter` and
  leaves the top-level command list about the manifest rather than two loose verbs.
- Keep `--json` only on `pipx list`, where it prints the versioned package snapshot that `install-all` reads back. Every
  other command dropped the `--json` alias in favour of `--output json`, so the snapshot format and the result envelope no
  longer share a flag.
- Name the existing-environment argument `ENVIRONMENT` across `inject`, `uninject`, `expose`, `unexpose`, `pin`, `unpin`,
  `uninstall`, `reinstall`, and `exec`, and fix the `uninject` help, which described the argument as the environment to
  inject into rather than uninject from.
- Record the interpreter and backend in the structured `install`, `upgrade`, and `upgrade-all` results, list
  `PIPX_GLOBAL_COMPLETION_DIR` in `pipx environment`, and show the shell-completion directory in `pipx list`. Completions
  had a global override that pipx honoured but never surfaced, and the records omitted which Python and backend produced a
  venv.
- Rename `--include-apps-from` to `--include-resources-from` and the manifest key to match. The option always exposed
  manual pages and shell completions alongside apps, so the new name describes what it does; `--include-apps` keeps its
  name. A venv recorded under the old key is migrated on read.


Bugfixes
--------

- Check a candidate interpreter's real patch version against `requires-python`. pipx matched only on the minor version, so
  it rejected an installed `3.13.7` for `>=3.13.5` and accepted `3.14.6` for `<3.14.1`. It now queries each resolved
  interpreter and keeps the first whose full version satisfies the constraint. (:issue:`387`)
- Keep existing exposed files when copy-based environments provide the same resource name. (:issue:`540`)
- Recover custom paths when pipx manages its own installation on Unix. (:issue:`774`)
- Keep install failures in JSON with the correct environment. (:issue:`828`)
- Show injected apps in `pipx list` on systems that copy launchers. (:issue:`997`)
- Serialize shared-library maintenance across pipx processes. (:issue:`1056`)
- Wait for an installation before listing its environment. (:issue:`1056`)
- Draw the installer progress bar while the download runs. pipx reads the installer output over a pipe, which hid the
  terminal from `pip`, so `pip` held its bar back and printed a finished one once the download had ended. (:issue:`1069`)
- Preserve symlinks in `PIPX_HOME` when creating environments. (:issue:`1327`)
- Create Windows launchers for PEP 723 scripts. (:issue:`1388`)
- Preserve the terminal encoding for applications started by `pipx run`. (:issue:`1423`)
- Make `ensurepath --global` update the system PATH configuration instead of root's shell profiles. (:issue:`1452`)
- Refresh `pipx_metadata.json` after `pipx runpip ... install` replaces the main package, so future `upgrade` and
  `reinstall` commands stop following a stale editable source path. (:issue:`1473`)
- Accept bare local Git and Mercurial URLs such as `git+file:///path/to/repository@revision`. (:issue:`1583`)
- Recreate the shared environment when pip cannot run. (:issue:`1606`)
- Resolve local `--find-links` paths before pipx changes the working directory. (:issue:`1637`)
- Keep pipx startup usable when locked files prevent trash cleanup. (:issue:`1847`)
- Fix `pipx run --with` being silently dropped for PEP 723 scripts on the pip backend; the extra packages are now
  installed into the temporary venv. (:issue:`1850`)
- Fix `pipx uninject` leaving the injected package's man page symlinks behind. (:issue:`1853`)
- Preserve `--editable` when installing a local package after a non-local package. (:issue:`1856`)
- Emit path warnings after logging setup for the active local or global context. (:issue:`1856`)
- Treat empty values for pipx path environment variables as unset. (:issue:`1856`)
- Apply a 30-second timeout to standalone Python index and archive network requests. (:issue:`1856`)
- Enforce pip's minimum supported version when shared-library upgrades include a user pin. (:issue:`1856`)
- Remove exposed apps that use a venv suffix when uninjecting packages. (:issue:`1856`)
- Report corrupt venv metadata as missing without aborting list and bulk commands. (:issue:`1856`)
- Return user-set values for the advertised `pipx environment --value` choices. (:issue:`1856`)
- Keep existing venv metadata when pipx cannot write its replacement. (:issue:`1856`)
- Keep trash cleanup non-fatal during directory races and failed moves. (:issue:`1856`)
- List only packages whose pin state changed during `pipx unpin`. (:issue:`1856`)
- Reject both Windows path separators in package names. (:issue:`1856`)
- Resolve relative paths in attached `-c` and `-f` pip arguments before invoking pip. (:issue:`1856`)
- Support standalone Python downloads on Windows ARM64. (:issue:`1856`)
- Avoid import crashes when stderr or its encoding is unavailable. (:issue:`1856`)
- Keep Windows uninject working while an exposed app runs. (:issue:`1856`)
- Translate pip binary and trusted-host options to valid uv run arguments, and reject `--no-deps` before invoking uv. (:issue:`1856`)
- Validate members before extracting a standalone Python archive on Python 3.10.0-3.10.11, which predate tarfile's data
  filter. pipx now refuses any entry whose path or link target would escape the download directory instead of falling back
  to an unfiltered extraction. (:issue:`1856`)
- Return a resolution error when standalone Python lacks a build for the current platform. (:issue:`1856`)
- Prevent `install --force` from saving its internal `--force-reinstall` option in package metadata. (:issue:`1856`)
- Continue bulk interpreter upgrades after finding a corrupt standalone interpreter. (:issue:`1856`)
- Skip shared-library maintenance for no-op installs. (:issue:`1856`)
- Compare metadata versions by parsed release components when selecting shared libraries. (:issue:`1856`)
- Wait for the animation thread to stop before clearing its final frame. (:issue:`1856`)
- Preserve standalone archive extraction on Python 3.10 releases without the tar filter API. (:issue:`1856`)
- Preserve noncanonical package prefixes when completing names of installed virtual environments. (:issue:`1856`)
- Preserve stored pip arguments for injected packages during `pipx upgrade --include-injected`. (:issue:`1856`)
- Preserve caller-owned pip arguments when creating the shared-library environment. (:issue:`1856`)
- Use tar's data filter when extracting standalone Python archives for consistent safety. (:issue:`1856`)
- Skip cache tag files when removing expired `pipx run` environments. (:issue:`1856`)
- Allow forced installs in existing uv environments. (:issue:`1924`)
- Store the venv cache and the logs in the platform cache and log directories on every platform, and keep them out of a
  pipx home that only exists for backwards compatibility. Setting `PIPX_HOME` still keeps both inside it. (:issue:`1946`)
- Apply `pipx manifest lock` as all-or-nothing. When a manifest declares locks for several tools, pipx wrote the
  regenerated files one at a time, so a failure partway left some locks new and others old. Each target is now backed up
  before it is replaced and every applied lock is rolled back if any replacement fails.
- Apply a 30-second timeout and a 10 MiB size limit when downloading a remote `pipx run` or `pipx install` script, so a
  stalled or oversized URL can no longer hang pipx or exhaust memory. `pipx run` also accepts a script URL with a query
  string, such as `tool.py?raw=1`, by matching on the URL path.
- Gate a PyPI release on the test suite and validate the built artifacts before publishing. The release workflow now runs
  the full test matrix for the tagged commit, checks the distributions with `twine`, and confirms the built version
  matches the tag, so a broken build or a mismatched tag cannot reach PyPI.
- Honour a script's PEP 723 `requires-python` on the pip-backed `pipx run`. Without an explicit `--python`, pipx now picks
  an interpreter that satisfies the constraint, matching what the uv backend already does; with an explicit `--python`
  that fails the constraint it reports a clear error instead of running on an unsupported interpreter. A malformed inline
  metadata block now produces a readable message rather than a traceback.
- Include `pipx run --with` packages in the run-cache key. Because they were absent, `pipx run TOOL` and
  `pipx run --with EXTRA TOOL` shared one cached environment, so extras injected by one invocation leaked into later runs
  that asked for none. Each distinct set of extras now gets its own environment, and the extras are injected only when
  that environment is first built.
- Keep the backups that `install --force` and `reinstall` take while replacing an environment in pipx's trash rather than
  beside the live environments. A backup placed in the venvs directory was picked up as a broken environment by a
  concurrent `list` or `reinstall-all`; the trash shares the home's filesystem, so restoring a backup is still an atomic
  rename.
- Make a standalone Python upgrade atomic. pipx used to delete the existing interpreter before downloading its
  replacement, so a failed download or unpack left no interpreter at all. The new build is now staged beside the old one
  and swapped in only once it is complete, and a failed swap restores the previous build.
- Make the expired-cache sweep that runs before `pipx run` non-blocking. pipx used to wait for a lock on every other
  cached environment, so a concurrent `pipx run` whose install held one of those locks stalled the new run, a stall that
  lasted the whole install on Windows. The sweep now skips any environment another run is holding.
- Probe a `uv` found on `PATH` before using it, and bound every `uv --version` call with a timeout. A broken or hanging
  `uv` on `PATH` previously slipped past discovery and stalled the next command; pipx now skips such a binary and reports
  a clear error instead of hanging.
- Reject a `--suffix` that contains anything but letters, digits, and the characters `.` `_` `-` `+` `@`. A suffix is
  spliced straight into the names of the links pipx writes into `PIPX_BIN_DIR` and `PIPX_MAN_DIR`, so a value such as
  `/../../owned` could previously place those links outside pipx's own directories.
- Remove a dropped app or man page during upgrade only when pipx still owns the exposed file, so a command a user or
  another package replaced is left in place.
- Report `pipx expose` as a partial or failed operation when a resource cannot be linked because a foreign file already
  occupies its target name. The command previously claimed success while silently leaving those apps or manual pages
  unexposed; it now lists each conflict in the structured result and exits non-zero.
- Stop forcing `UV_NO_PROGRESS=1` on every uv call. The override silenced uv's progress bar even when pipx asked to draw
  one, and it ignored a `UV_NO_PROGRESS` already set in the environment. pipx now suppresses the bar only in quiet, JSON,
  and non-interactive runs, and defers to the caller's `UV_NO_PROGRESS` when it does want progress shown.
- Track exposed shell completions through the full environment lifecycle. Stale-resource cleanup during install, upgrade,
  and reinstall, the repair relink check, and the ownership filter now include completions alongside apps and manual
  pages, so a completion a package stops shipping is removed instead of lingering.


Improved Documentation
----------------------

- Document the pipx application scope and feature boundaries. (:issue:`177`)


Deprecations and Removals
-------------------------

- Remove the `PIPX_HOME_ALLOW_SPACE` environment variable and the warning about spaces in the pipx home path. `pip` and
  `uv` both write a `/bin/sh` wrapper as the shebang when the interpreter path contains a space, so applications installed
  into such a path run. (:issue:`1946`)


`1.15.0 <https://github.com/pypa/pipx/tree/1.15.0>`_ - 2026-06-24
=================================================================

Features
--------

- Add a ``--dry-run`` flag to ``pipx ensurepath`` that reports which directories would be added to ``PATH`` without
  modifying ``PATH`` or any shell configuration file. (:issue:`1014`)

Bugfixes
--------

- Fix ``pipx uninject`` for uv-backed environments, where uv lacks pip's ``list --not-required`` option. Both backends
  now derive the not-required set from installed distribution metadata, so they behave identically, and a dependency
  pulled in only by another package's extra is kept instead of being treated as removable. (:issue:`1841`)

`1.14.1 <https://github.com/pypa/pipx/tree/1.14.1>`_ - 2026-06-17
=================================================================

Bugfixes
--------

- Restore the original package if ``pipx reinstall-all`` is interrupted during reinstall. (:issue:`966`)
- Allow importing ``pipx.util`` before ``pipx.paths``. (:issue:`1333`)
- Ensure ``pipx inject --force`` reinstalls injected packages without persisting the force-reinstall option in package
  metadata. (:issue:`1545`)
- Preserve installer errors when package-name detection fails during local package installs. (:issue:`1567`)
- Expose manual pages for editable local package installs. (:issue:`1793`)
- Fixed ``pipx pin <app> --injected-only`` so it can pin injected packages when the main app is already pinned.
  (:issue:`1835`)

`1.14.0 <https://github.com/pypa/pipx/tree/1.14.0>`_ - 2026-06-04
=================================================================

Features
--------

- Add ``--no-path-check`` to ``pipx run`` to skip the warning when the app is already on ``PATH``. Useful for shim
  scripts that wrap ``pipx run <app>`` under the same name as the app. (:issue:`1824`)

Bugfixes
--------

- Add regression coverage for ``pipx inject`` accepting ``--force`` before or after injected dependencies.
  (:issue:`1444`)

Improved Documentation
----------------------

- Use the bootstrap pipx executable when adding PATH in self-managed installs. (:issue:`1481`)

`1.13.0 <https://github.com/pypa/pipx/tree/1.13.0>`_ - 2026-05-30
=================================================================

Features
--------

- Add ``PIPX_DISABLE_SHARED_LIBS_AUTO_UPGRADE`` to skip automatic shared library upgrades. (:issue:`1650`)
- Update the error message in get-pipx.py; it is obsoleted, not deprecated. (:issue:`1813`)

Bugfixes
--------

- Install app scripts with shebangs that ignore ``PYTHONPATH``. (:issue:`1584`)
- Refresh cached standalone Python indexes written by older pipx versions before using ``--fetch-missing-python``.
  (:issue:`1774`)

Improved Documentation
----------------------

- Document how to clear cache warnings from ``runpip``. (:issue:`1802`)

`1.12.0 <https://github.com/pypa/pipx/tree/1.12.0>`_ - 2026-05-06
=================================================================

Features
--------

- Add ``--fetch-python`` and ``PIPX_FETCH_PYTHON`` to control standalone Python downloads, with values ``always``,
  ``missing``, or ``never``. (:issue:`1663`)
- Add an opt-in ``uv`` backend. Install ``pipx[uv]`` (or put ``uv`` on ``PATH``) and pipx will create venvs with
  ``uv venv``, manage packages with ``uv pip``, and run ephemeral apps via ``uv tool run``.

  **Default change:** when ``uv`` is reachable, pipx uses it for **new** venvs by default. Existing venvs keep their
  recorded backend; flipping a venv requires ``pipx reinstall NAME --backend X``. Set ``PIPX_DEFAULT_BACKEND=pip`` to
  force pip even when uv is available, or pass ``--backend pip`` per command. ``pipx install pip`` always picks the pip
  backend (uv venvs have no pip).

  Selection precedence: ``--backend`` > recorded venv metadata > ``PIPX_DEFAULT_BACKEND`` > auto-detect. The env var
  sits *below* metadata so setting ``PIPX_DEFAULT_BACKEND=uv`` does not silently retarget existing pip-backed venvs; the
  recorded backend wins until you flip it explicitly. ``pipx environment`` exposes the resolved backend and its source
  as ``PIPX_RESOLVED_BACKEND`` and ``PIPX_BACKEND_SOURCE``.

  **Metadata version bump:** the venv metadata file format moves from ``0.5`` to ``0.6`` to record the chosen backend.
  Running this pipx version against an existing venv rewrites its metadata to ``0.6`` on the next install/upgrade. If
  you downgrade pipx after that, the older version raises ``Unknown metadata version 0.6`` and you'll need to reinstall
  the affected venvs from the older pipx (``pipx reinstall NAME``). (:issue:`1808`)

Deprecations and Removals
-------------------------

- Deprecate ``--fetch-missing-python`` and ``PIPX_FETCH_MISSING_PYTHON``; both are now aliases for
  ``--fetch-python=missing`` / ``PIPX_FETCH_PYTHON=missing``. ``PIPX_FETCH_MISSING_PYTHON=0`` (and other falsy values)
  now disables fetching, where previously any value enabled it. The ``pipx.interpreter.find_python_interpreter``
  keyword ``fetch_missing_python: bool`` is replaced by ``fetch_python: FetchPythonOptions``. (:issue:`1663`)

`1.11.2 <https://github.com/pypa/pipx/tree/1.11.2>`_ - 2026-05-05
=================================================================

Features
--------

- Add ``pipx help`` and ``pipx help <command>`` aliases for existing help output. (:issue:`1535`)
- Drop support for Python 3.9. (:issue:`1786`)
- Replace if/elif command dispatch in main.py with argparse set_defaults. (:issue:`1794`)

`1.11.1 <https://github.com/pypa/pipx/tree/1.11.1>`_ - 2026-03-31
=================================================================

Bugfixes
--------

- Ignore ``PIP_TARGET`` environment variable to prevent pip from installing outside the venv. (:issue:`735`)
- Fix ``pipx install`` failing on Windows when the username contains non-Latin characters (e.g. cyrillic, Chinese).
  (:issue:`780`)
- Show installed version and suggest ``upgrade`` when ``install`` detects an existing installation. (:issue:`795`)
- ``--verbose`` and ``--quiet`` flags before the subcommand are no longer silently ignored. (:issue:`1282`)
- Remove dependency app symlinks when uninjecting a package that was injected with ``--include-deps``. (:issue:`1364`)
- Remove ``setuptools`` from shared libs to prevent version conflicts when app venvs use a different Python.
  (:issue:`1539`)
- Prevent ``uninject`` from removing dependencies still needed by other packages in the venv. (:issue:`1672`)

`1.11.0 <https://github.com/pypa/pipx/tree/1.11.0>`_ - 2026-03-23
=================================================================

Features
--------

- Add ``PIPX_MAX_LOGS`` environment variable to configure the maximum number of log files to keep. (:issue:`1570`)

Bugfixes
--------

- Allow ``--pip-args`` to be passed to ``upgrade-all``. (:issue:`1503`)
- Fix ``--pip-args='-c <url>'`` breaking when constraint target is a URL instead of a local path. (:issue:`1582`)
- Enable keyring authentication for private package indexes by setting ``PIP_KEYRING_PROVIDER=subprocess`` (:issue:`1603`)
- Added error handling for ``pip list`` command failures (:issue:`1698`)

Improved Documentation
----------------------

- Remove outdated "experimental" note from ``--suffix`` help text. (:issue:`1621`)

`1.10.1 <https://github.com/pypa/pipx/tree/1.10.1>`_ - 2026-03-20
=================================================================

Bugfixes
--------

- Use stored pip_args from install metadata when running ``pipx upgrade`` without explicit ``--pip-args`` (:issue:`1441`)
- Fix ``--global`` flag being silently ignored when placed before the subcommand (:issue:`1443`)
- Respect ``--quiet`` flag in ``install`` and suppress animations and success messages (:issue:`1508`)
- Catch missing Python interpreter in ``upgrade`` and show helpful error instead of crashing (:issue:`1602`)
- Prevent data loss by rejecting relative paths in ``uninstall``, ``reinstall``, and other package-name arguments
  (:issue:`1718`)

`1.10.0 <https://github.com/pypa/pipx/tree/1.10.0>`_ - 2026-03-18
=================================================================

Features
--------

- Add ``--with`` flag to ``pipx run`` to allow injecting dependencies (:issue:`1607`)
- add more specific directions in the logs towards a resolution if you have a space in the PIX_HOME path (:issue:`1634`)

Bugfixes
--------

- Fixed upgrade command failing when package name includes extras (e.g., ``pipx upgrade "coverage[toml]"``).
  (:issue:`925`)
- Fix run command with bash substitution (e.g. ``pipx run <(pbpaste)``) (:issue:`1293`)
- Allow ``pipx runpip`` to split single string arguments. (:issue:`1520`)
- Fix handling of shared libraries when the original Python interpreter is removed on Windows by detecting stale venv
  references and recreating the shared libraries with the current Python. (:issue:`1723`)

Misc
----

- :issue:`1638`, :issue:`1731`

`1.9.0 <https://github.com/pypa/pipx/tree/1.9.0>`_ - 2026-03-17
===============================================================

Features
--------

- Add completion choices for ``pipx environment --value``. (:issue:`1498`)

Bugfixes
--------

- Ignore recursive symlink loops in PIPX_BIN_DIR. (:issue:`1592`)
- ``pipx reinstall``: An exception will now be raised if package is pinned. (:issue:`1611`)
- Stop ``pipx run`` from leaving bad temporary venvs when first installation was unsuccessful. (:issue:`1709`)

`1.8.0 <https://github.com/pypa/pipx/tree/1.8.0>`_ - 2025-09-30
===============================================================

Features
--------

- Rename environmental variable ``USE_EMOJI`` to ``PIPX_USE_EMOJI``. (:issue:`1395`)
- Add ``--all-shells`` flag to ``pipx ensurepath``. (:issue:`1585`)
- Add support for Python 3.13 (:issue:`1647`)

Bugfixes
--------

- On Windows, no longer overwrite existing files on upgrade if source and destination are the same (:issue:`683`)
- Update the logic of finding python interpreter such that ``--fetch-missing-python`` works on Windows (:issue:`1521`)
- Fix no message displayed when no packages are upgraded with ``upgrade-all``. (:issue:`1565`)
- Fix incorrect order of flags when using ``pipx upgrade``. (:issue:`1610`)
- Update the archive name of build of Python for Windows (:issue:`1630`)
- Set up standalone python fetching to use checksums directly from the GitHub API. (:issue:`1652`)
- Fix running a script with explicitly empty ``dependencies = []``. (:issue:`1658`)

Improved Documentation
----------------------

- Fix ``/changelog/`` and ``/contributing/`` docs URLs (:issue:`1540`)

`1.7.1 <https://github.com/pypa/pipx/tree/1.7.1>`_ - 2024-08-23
===============================================================

Bugfixes
--------

- Use minimum supported Python to build zipapp in release action such that ``tomli`` is included in it. (:issue:`1514`)

`1.7.0 <https://github.com/pypa/pipx/tree/1.7.0>`_ - 2024-08-22
===============================================================

Features
--------

- Add a ``--prepend`` option to the ``pipx ensurepath`` command to allow prepending ``pipx``'s location to ``PATH``
  rather than appending to it. This is useful when you want to prioritize ``pipx``'s executables over other executables
  in your ``PATH``. (:issue:`1451`)
- List ``PIPX_GLOBAL_[HOME|BIN_DIR|MAN_DIR]`` in ``pipx environment``. (:issue:`1492`)

Bugfixes
--------

- Introduce ``PIPX_HOME_ALLOW_SPACE`` environment variable, to silence the spaces in pipx home path warning
  (:issue:`1320`)
- Fix passing constraints file path into ``pipx install`` operation via ``pip`` args (:issue:`1389`)
- Add help messages for ``pipx pin`` and ``pipx unpin`` commands. (:issue:`1438`)
- Stop ``pipx install --global`` from installing files in ``~/.local``. (:issue:`1475`)
- Fix installation abortion on multiple packages when one or more are already installed. (:issue:`1509`)

Improved Documentation
----------------------

- Move all documentation files to the ``docs`` directory. (:issue:`1479`)

`1.6.0 <https://github.com/pypa/pipx/tree/1.6.0>`_ - 2024-06-01
===============================================================

Features
--------

- Add ``install-all`` command to install packages according to spec metadata file. (:issue:`687`)
- Introduce ``pipx pin`` and ``pipx unpin`` commands, which can be used to pin or unpin the version of an installed
  package, so it will not be upgraded by ``pipx upgrade`` or ``pipx upgrade-all``. (:issue:`891`)
- Add a new option ``--pinned`` to ``pipx list`` command for listing pinned packages only. (:issue:`891`)
- Add ``pipx interpreter upgrade`` command to upgrade local standalone python in micro/patch level (:issue:`1249`)
- Add ``--requirement`` option to ``inject`` command to read list of packages from a text file. (:issue:`1252`)
- Add ``pipx upgrade-shared`` command, to create/upgrade shared libraries as a standalone command. (:issue:`1316`)
- Allow ``upgrade`` command to accept multiple packages as arguments. (:issue:`1336`)
- Support Python version for ``--python`` arg when py launcher is not available (:issue:`1342`)
- Make ``install-all`` gather errors in batch (:issue:`1348`)

Bugfixes
--------

- Resolve the ``DEFAULT_PYTHON`` to the actual absolute path (:issue:`965`)
- Fix error log overwrite for "-all" batch operations. (:issue:`1132`)
- Do not reinstall already injected packages without ``--force`` being passed. (:issue:`1300`)
- Only show ``--python`` and ``--force`` flag warning if both flags are present (:issue:`1304`)
- Don't allow paths to be passed into ``pipx reinstall``, as this might wreak havoc. (:issue:`1324`)
- Make the Python ``venv`` module arguments work with ``upgrade --install`` (:issue:`1344`)
- Fix version check for standalone python (:issue:`1349`)
- Validate package(s) argument should not be path(s). (:issue:`1354`)
- Validate whether a package is an URL correctly. (:issue:`1355`)
- Support python3.8 for standalone python builds (:issue:`1375`)
- Install specified version of ``--preinstall`` dependency instead of latest version (:issue:`1377`)
- Move ``--global`` option into shared parser, such that it can be passed after the subcommand, for example
  ``pipx ensurepath --global``. (:issue:`1397`)
- Fix discovery of a ``pipx run`` entry point if a local path was given as package. (:issue:`1422`)

Improved Documentation
----------------------

- Create a dedicated section for manual pages and add an example with ``pdm-backend``. (:issue:`1312`)
- Add example, test and cli help description how to install multiple packages with the --preinstall flag (:issue:`1321`)
- Refine docs generation script and template. (:issue:`1325`)
- Add a note about sourcing the shell config file for ``ensure_path`` (:issue:`1346`)

`1.5.0 <https://github.com/pypa/pipx/tree/1.5.0>`_ - 2024-03-29
===============================================================

Features
--------

- Add ``--global`` option to ``pipx`` commands.

  - This will run the action in a global scope and affect environment for all system users. (:issue:`754`)

- Add a ``--fetch-missing-python`` flag to all commands that accept a ``--python`` flag.

  - When combined, this will automatically download a standalone copy of the requested python version if it's not
    already available on the user's system. (:issue:`1242`)

- Add commands to list and prune standalone interpreters (:issue:`1248`)
- Revert platform-specific directories on MacOS and Windows

  - They were leading to a lot of issues with Windows sandboxing and spaces in shebangs on MacOS. (:issue:`1257`)

- Add ``--install`` option to ``pipx upgrade`` command.

  - This will install the package given as argument if it is not already installed. (:issue:`1262`)

Bugfixes
--------

- Correctly resolve home directory in pipx directory environment variables. (:issue:`94`)
- Pass through ``pip`` arguments when upgrading shared libraries. (:issue:`964`)
- Fix installation issues when files in the working directory interfere with venv creation process. (:issue:`1091`)
- Report correct filename in tracebacks with ``pipx run <scriptname>`` (:issue:`1191`)
- Let self-managed pipx uninstall itself on windows again. (:issue:`1203`)
- Fix path resolution for python executables looked up in PATH on windows. (:issue:`1205`)
- Display help message when ``pipx install`` is run without arguments. (:issue:`1266`)
- Fix crashes due to superfluous ``-q`` flags by discarding exceeding values (:issue:`1283`)

Improved Documentation
----------------------

- Update the completion instructions for zipapp users. (:issue:`1072`)
- Update the example for running scripts with dependencies. (:issue:`1227`)
- Update the docs for package developers on the use of configuration using pyproject.toml (:issue:`1229`)
- Add installation instructions for Fedora (:issue:`1239`)
- Update the examples for installation from local dir (:issue:`1277`)
- Fix inconsistent wording in ``pipx install`` command description. (:issue:`1307`)

Deprecations and Removals
-------------------------

- Deprecate ``--skip-maintenance`` flag of ``pipx list``; maintenance is now never executed there (:issue:`1256`)

Misc
----

- :issue:`1296`

`1.4.3 <https://github.com/pypa/pipx/tree/1.4.3>`_ - 2024-01-16
===============================================================

Bugfixes
--------

- Autofix python version for pylauncher, when version is provided prefixed with ``python`` (:issue:`1150`)
- Support building pipx wheels with setuptools-scm<7, such as on FreeBSD. (:issue:`1208`)

Improved Documentation
----------------------

- Provide useful error messages when unresolvable python version is passed (:issue:`1150`)
- Introduce towncrier for managing the changelog (:issue:`1161`)
- Add workaround for using pipx applications in shebang under macOS (:issue:`1198`)

`1.4.2 <https://github.com/pypa/pipx/tree/1.4.2>`_
==================================================

Features
--------

- Allow skipping maintenance tasks during list command
- Raise more user friendly error when provided ``--python`` version is not found
- Update ``pipx run`` on scripts using ``/// script`` and no ``run`` table following the updated version of PEP 723
  (#1180)

Bugfixes
--------

- Include ``tomli`` into ``pipx.pyz`` (zipapp) so that it can be executed with Python 3.10 or earlier (#1142)
- Fix resolving the python executable path on linux
- ``pipx run``: Verify whether the script name provided is a file before running it
- Avoid repeated exception logging in a few rare cases (#1192)

`1.4.1 <https://github.com/pypa/pipx/tree/1.4.1>`_
==================================================

Bugfixes
--------

- Set default logging level to WARNING, so debug log messages won't be shown without passing additional flags such as
  ``--verbose``

`1.4.0 <https://github.com/pypa/pipx/tree/1.4.0>`_
==================================================

Features
--------

- Add ``--quiet`` and ``--verbose`` options for the ``pipx`` subcommands
- Add ability to install multiple packages at once
- Delete directories directly instead of spawning rmdir on Windows

Improved Documentation
----------------------

- Add Scoop installation instructions

Bugfixes
--------

- "Failed to delete" error when using Microsoft Store Python
- "No pyvenv.cfg file" error when using Microsoft Store Python (#1164)

`1.3.3 <https://github.com/pypa/pipx/tree/1.3.3>`_
==================================================

Improved Documentation
----------------------

- Make the logo more visible in dark mode

`1.3.2 <https://github.com/pypa/pipx/tree/1.3.2>`_
==================================================

Features
--------

- The project version number is now dynamic and generated from the VCS at build time

Improved Documentation
----------------------

- Add additional example for --pip-args option, to docs/examples.md

`1.3.1 <https://github.com/pypa/pipx/tree/1.3.1>`_
==================================================

Bugfixes
--------

- Fix combining of --editable and --force flag

`1.3.0 <https://github.com/pypa/pipx/tree/1.3.0>`_
==================================================

Features
--------

- Allow running ``pip`` with ``pipx run``
- Add ``--with-suffix`` for ``pipx inject`` command
- ``pipx install``: emit a warning when ``--force`` and ``--python`` were passed at the same time
- Add explicit 3.12 support
- Make usage message in ``pipx run`` show ``package_or_url``, so extra will be printed out as well
- Use the py launcher, if available, to select Python version with the ``--python`` option
- add pre-commit hook support
- Add ``pipx install --preinstall`` to support preinstalling build requirements
- Return an error message when directory can't be added to PATH successfully
- Expose manual pages included in an application installed with ``pipx install``
- Check whether pip module exists in shared lib before performing any actions, such as ``reinstall-all``.
- Drop ``setuptools`` and ``wheel`` from the shared libraries. This results in less time consumption when the libraries
  are automatically upgraded.
- Support `inline script metadata
  <https://packaging.python.org/en/latest/specifications/inline-script-metadata/>`_ in ``pipx run``.
- Imply ``--include-apps`` when running ``pipx inject --include-deps``
- Add ``--force-reinstall`` to pip arguments when ``--force`` was passed
- Support including requirements in scripts run using ``pipx run`` (#916)
- Pass ``pip_args`` to ``shared_libs.upgrade()``
- Fallback to user's log path if the default log path (``$PIPX_HOME/logs``) is not writable to aid with pipx being used
  for multi-user (e.g. system-wide) installs of applications
- Don't show escaped backslashes for paths in console output
- Move ``pipx`` paths to ensure compatibility with the platform-specific user directories
- Pass ``--no-input`` to pip when output is not piped to parent stdout
- Print all environment variables in ``pipx environment``

Improved Documentation
----------------------

- Add more examples for ``pipx run``
- Add subsection to make README easier to read

Deprecations and Removals
-------------------------

- Drop support for Python 3.7

Bugfixes
--------

- Fix wrong interpreter usage when injecting local pip-installable dependencies into venvs
- Fix program name in generated manual page

`1.2.1 <https://github.com/pypa/pipx/tree/1.2.1>`_
==================================================

Bugfixes
--------

- Fix compatibility to packaging 23.2+ by removing reliance on packaging's requirement validation logic and detecting a
  URL-based requirement in pipx. (#1070)

`1.2.0 <https://github.com/pypa/pipx/tree/1.2.0>`_
==================================================

Features
--------

- Add ``pipx uninject`` command (#820)
- Ship a `zipapp <https://docs.python.org/3/library/zipapp.html>`_ of pipx
- Match pip's behaviour when package name ends with archive extension (treat it as a path)
- Change the program name to ``path/to/python -m pipx`` when running as ``python -m pipx``
- Improve the detection logic for MSYS2 to avoid entering infinite loop (#908) (#938)
- Remove extra trailing quote from exception message
- Fix EncodingWarning in ``pipx_metadata_file``.

Improved Documentation
----------------------

- Add an example for installation from source with extras
- Fix ``pipx run`` examples and update Python versions used by ``pipx install`` examples

Bugfixes
--------

- Add test for pip module in ``pipx reinstall`` to fix an issue with ``pipx reinstall-all`` (#935)

`1.1.0 <https://github.com/pypa/pipx/tree/1.1.0>`_
==================================================

Features
--------

- Add ``pipx environment`` command (#793)
- Add ``list --short`` option to list only package names (#804)
- Improve the behaviour of ``shlex.split`` on Windows, so paths on Windows can be handled properly when they are passed
  in ``--pip-args``. (#794)
- [dev] Change github action job names
- Add additional examples for installation from git repos
- [packaging] Switch to `PEP 621 <https://www.python.org/dev/peps/pep-0621/>`_
- Add a CACHEDIR.TAG to the cache directory to prevent it from being included in archives and backups. For more
  information about cache directory tags, see https://bford.info/cachedir

Bugfixes
--------

- Fix encoding issue on Windows when pip fails to install a package

Improved Documentation
----------------------

- Add more examples
- Fix the command for `installing development version
  <https://pipx.pypa.io/stable/installation/#install-pipx-development-versions>`_. (#801)
- Fix test status badge in readme file

`1.0.0 <https://github.com/pypa/pipx/tree/1.0.0>`_
==================================================

Features
--------

- Support `argcomplete 2.0.0 <https://pypi.org/project/argcomplete/2.0.0>`_ (#790)
- Include machinery to build a manpage for pipx with `argparse-manpage <https://pypi.org/project/argparse-manpage/>`_.
- Add better handling for 'app not found' when a single app is present in the project, and an improved error message
  (#733)

Bugfixes
--------

- Fixed animations sending output to stdout, which can break JSON output. (#769)
- Fix typo in ``pipx upgrade-all`` output

`0.17.0 <https://github.com/pypa/pipx/tree/0.17.0>`_
====================================================

- Support ``pipx run`` with version constraints and extras. (#697)

`0.16.5 <https://github.com/pypa/pipx/tree/0.16.5>`_
====================================================

- Fixed ``pipx list`` output phrasing to convey that python version displayed is the one with which package was
  installed.
- Fixed ``pipx install`` to provide return code 0 if venv already exists, similar to pip's behavior. (#736)
- [docs] Update ansible's install command in `Programs to Try document
  <https://pipx.pypa.io/stable/programs-to-try/#ansible>`_ to work with Ansible 2.10+ (#742)

`0.16.4 <https://github.com/pypa/pipx/tree/0.16.4>`_
====================================================

- Fix to ``pipx ensurepath`` to fix behavior in user locales other than UTF-8, to fix #644. The internal change is to
  use userpath v1.6.0 or greater. (#700)
- Fix virtual environment inspection for Python releases that uses an int for its release serial number. (#706)
- Fix PermissionError in windows when pipx manages itself. (#718)

`0.16.3 <https://github.com/pypa/pipx/tree/0.16.3>`_
====================================================

- Organization: pipx is extremely pleased to now be a project of the Python Packaging Authority (PyPA)! Note that our
  github URL has changed to `pypa/pipx <https://github.com/pypa/pipx>`_
- Fixed ``pipx list --json`` to return valid json with no venvs installed. Previously would return an empty string to
  stdout. (#681)
- Changed ``pipx ensurepath`` bash behavior so that only one of {``~/.profile``, ``~/.bash_profile``} is modified with
  the extra pipx paths, not both. Previously, if a ``.bash_profile`` file was created where one didn't exist, it could
  cause problems, e.g. #456. The internal change is to use userpath v1.5.0 or greater. (#684)
- Changed default nox tests, Github Workflow tests, and pytest behavior to use local pypi server with fixed lists of
  available packages. This allows greater test isolation (no network pypi access needed) and determinism (fixed
  available dependencies.) It also allows running the tests offline with some extra preparation beforehand (See
  `Running Unit Tests Offline <https://pipx.pypa.io/stable/contributing/#running-unit-tests-offline>`_). The old style
  tests that use the internet to access pypi.org are still available using ``nox -s tests_internet`` or
  ``pytest --net-pypiserver tests``. (#686)
- Colorama is now only installed on Windows. (#691)

`0.16.2.1 <https://github.com/pypa/pipx/tree/0.16.2.1>`_
========================================================

- Changed non-venv-info warnings and notices from ``pipx list`` to print to stderr. This especially prevents
  ``pipx list --json`` from printing invalid json to stdout. (#680)
- Fixed bug that could cause uninstall on Windows with injected packages to uninstall too many apps from the local
  binary directory. (#679)

`0.16.2.0 <https://github.com/pypa/pipx/tree/0.16.2.0>`_
========================================================

- Fixed bug #670 where uninstalling a venv could erroneously uninstall other apps from the local binary directory.
  (#672)
- Added ``--json`` switch to ``pipx list`` to output rich json-metadata for all venvs.
- Ensured log files are utf-8 encoded to prevent Unicode encoding errors from occurring with emojis. (#646)
- Fixed issue which made pipx incorrectly list apps as part of a venv when they were not installed by pipx. (#650)
- Fixed old regression that would prevent pipx uninstall from cleaning up linked binaries if the venv was old and did
  not have pipx metadata. (#651)
- Fixed bugs with suffixed-venvs on Windows. Now properly summarizes install, and actually uninstalls associated
  binaries for suffixed-venvs. (#653)
- Changed venv minimum python version to 3.6, removing python 3.5 which is End of Life. (#666)

`0.16.1.0 <https://github.com/pypa/pipx/tree/0.16.1.0>`_
========================================================

- Introduce the ``pipx.run`` entry point group as an alternative way to declare an application for ``pipx run``.
- Fix cursor show/hide to work with older versions of Windows. (#610)
- Support text colors on Windows. (#612)
- Better platform unicode detection to avoid errors and allow showing emojis when possible. (#614)
- Don't emit show cursor or hide cursor codes if STDERR is not a tty. (#620)
- Sped up ``pipx list`` (#624).
- pip errors no longer stream to the shell when pip fails during a pipx install. pip's output is now saved to a log
  file. In the shell, pipx will tell you the location of the log file and attempt to summarize why pip failed. (#625)
- For ``reinstall-all``, fixed bug where missing python executable would cause error. (#634)
- Fix regression which prevented pipx from working with pythonloc (and ``__pypackages__`` folder). (#636)

`0.16.0.0 <https://github.com/pypa/pipx/tree/0.16.0.0>`_
========================================================

- New venv inspection! The code that pipx uses to examine and determine metadata in an installed venv has been made
  faster, better, and more reliable. It now uses modern python libraries like ``packaging`` and ``importlib.metadata``
  to examine installed venvs. It also now properly handles installed package extras. In addition, some problems pipx
  has had with certain characters (like periods) in package names should be remedied.
- Added reinstall command for reinstalling a single venv.
- Changed ``pipx run`` on non-Windows systems to actually replace pipx process with the app process instead of running
  it as a subprocess. (Now using python's ``os.exec*``)
- [bugfix] Fixed bug with reinstall-all command when package have been installed using a specifier. Now the initial
  specifier is used.
- [bugfix] Override display of ``PIPX_DEFAULT_PYTHON`` value when generating web documentation for ``pipx install`` #523
- [bugfix] Wrap help documentation for environment variables.
- [bugfix] Fixed uninstall crash that could happen on Windows for certain packages
- [feature] Venv package name arguments now do not have to match exactly as pipx has them stored, but can be specified
  in any python-package-name-equivalent way. (i.e. case does not matter, and ``.``, ``-``, ``_`` characters are
  interchangeable.)
- [change] Venvs with a suffix: A suffix can contain any characters, but for purposes of uniqueness, python package
  name rules apply--upper- and lower-case letters are equivalent, and any number of ``.``, ``-``, or ``_`` characters
  in a row are equivalent. (e.g. if you have a suffixed venv ``pylint_1.0A`` you could not add another suffixed venv
  called ``pylint--1-0a``, as it would not be a unique name.)
- [implementation detail] Pipx shared libraries (providing pip, setuptools, wheel to pipx) are no longer installed
  using pip arguments taken from the last regular pipx install. If you need to apply pip arguments to pipx's use of pip
  for its internal shared libraries, use ``PIP_*`` environment variables.
- [feature] Autocomplete for venv names is no longer restricted to an exact match to the literal venv name, but will
  autocomplete any logically-similar python package name (i.e. case does not matter, and ``.``, ``-``, ``_`` characters
  are all equivalent.)
- pipx now reinstall its internal shared libraries when the user executes ``reinstall-all``.
- Made sure shell exit codes from every pipx command are correct. In the past some (like from ``pipx upgrade``) were
  wrong. The exit code from ``pipx runpip`` is now the exit code from the ``pip`` command run. The exit code from
  ``pipx list`` will be 1 if one or more venvs have problems that need to be addressed.
- pipx now writes a log file for each pipx command executed to ``$PIPX_HOME/logs``, typically ``~/.local/pipx/logs``.
  pipx keeps the most recent 10 logs and deletes others.
- ``pipx upgrade`` and ``pipx upgrade-all`` now have a ``--upgrade-injected`` option which directs pipx to also upgrade
  injected packages.
- ``pipx list`` now detects, identifies, and suggests a remedy for venvs with old-internal data (internal venv names)
  that need to be updated.
- Added a "Troubleshooting" page to the pipx web documentation for common problems pipx users may encounter.
- pipx error, warning, and other messages now word-wrap so words are not split across lines. Their appearance is also
  now more consistent.

`0.15.6.0 <https://github.com/pypa/pipx/tree/0.15.6.0>`_
========================================================

- [docs] Update license
- [docs] Display a more idiomatic command for registering completions on fish.
- [bugfix] Fixed regression in list, inject, upgrade, reinstall-all commands when suffixed packages are used.
- [bugfix] Do not reset package url during upgrade when main package is ``pipx``
- Updated help text to show description for ``ensurepath`` and ``completions`` help
- Added support for user-defined default python interpreter via new ``PIPX_DEFAULT_PYTHON``. Helpful for use with pyenv
  among other uses.
- [bugfix] Fixed bug where extras were ignored with a PEP 508 package specification with a URL.

`0.15.5.1 <https://github.com/pypa/pipx/tree/0.15.5.1>`_
========================================================

- [bugfix] Fixed regression of 0.15.5.0 which erroneously made installing from a local path with package extras not
  possible.

`0.15.5.0 <https://github.com/pypa/pipx/tree/0.15.5.0>`_
========================================================

- pipx now parses package specification before install. It removes (with warning) the ``--editable`` install option for
  any package specification that is not a local path. It also removes (with warning) any environment markers.
- Disabled animation when we cannot determine terminal size or if the number of columns is too small. (Fixes #444)
- [feature] Version of each injected package is now listed after name for ``pipx list --include-injected``
- Change metadata recorded from version-specified install to allow upgrades in future. Adds pipx dependency on
  ``packaging`` package.
- [bugfix] Prevent python error in case where package has no pipx metadata and advise user how to fix.
- [feature] ``ensurepath`` now also ensures that pip user binary path containing pipx itself is in user's PATH if pipx
  was installed using ``pip install --user``.
- [bugfix] For ``pipx install``, fixed failure to install if user has ``PIP_USER=1`` or ``user=true`` in pip.conf.
  (#110)
- [bugfix] Requiring userpath v1.4.1 or later so ensure Windows bug is fixed for ``ensurepath`` (#437)
- [feature] log pipx version (#423)
- [feature] ``--suffix`` option for ``install`` to allow multiple versions of same tool to be installed (#445)
- [feature] pipx can now be used with the Windows embeddable Python distribution

`0.15.4.0 <https://github.com/pypa/pipx/tree/0.15.4.0>`_
========================================================

- [feature] ``list`` now has a new option ``--include-injected`` to show the injected packages in the main apps
- [bugfix] Fixed bug that can cause crash when installing an app

`0.15.3.1 <https://github.com/pypa/pipx/tree/0.15.3.1>`_
========================================================

- [bugfix] Workaround multiprocessing issues on certain platforms (#229)

`0.15.3.0 <https://github.com/pypa/pipx/tree/0.15.3.0>`_
========================================================

- [feature] Use symlinks on Windows when symlinks are available

`0.15.2.0 <https://github.com/pypa/pipx/tree/0.15.2.0>`_
========================================================

- [bugfix] Improved error reporting during venv metadata inspection.
- [bugfix] Fixed incompatibility with pypy as venv interpreter (#372).
- [bugfix] Replaced implicit dependency on setuptools with an explicit dependency on packaging (#339).
- [bugfix] Continue reinstalling packages after failure
- [bugfix] Hide cursor while pipx runs
- [feature] Add environment variable ``USE_EMOJI`` to allow enabling/disabling emojis (#376)
- [refactor] Moved all commands to separate files within the commands module (#255).
- [bugfix] Ignore system shared libraries when installing shared libraries pip, wheel, and setuptools. This also fixes
  an incompatibility with Debian/Ubuntu's version of pip (#386).

`0.15.1.3 <https://github.com/pypa/pipx/tree/0.15.1.3>`_
========================================================

- [bugfix] On Windows, pipx now lists correct Windows apps (#217)
- [bugfix] Fixed a ``pipx install`` bug causing incorrect python binary to be used when using the optional --python
  argument in certain situations, such as running pipx from a Framework python on macOS and specifying a non-Framework
  python.

`0.15.1.2 <https://github.com/pypa/pipx/tree/0.15.1.2>`_
========================================================

- [bugfix] Fix recursive search of dependencies' apps so no apps are missed.
- ``upgrade-all`` now skips editable packages, because pip disallows upgrading editable packages.

`0.15.1.1 <https://github.com/pypa/pipx/tree/0.15.1.1>`_
========================================================

- [bugfix] fix regression that caused installing with --editable flag to fail package name determination.

`0.15.1.0 <https://github.com/pypa/pipx/tree/0.15.1.0>`_
========================================================

- Add Python 3.8 to PyPI classifier and travis test matrix
- [feature] auto-upgrade shared libraries, including pip, if older than one month. Hide all pip warnings that a new
  version is available. (#264)
- [bugfix] pass pip arguments to pip when determining package name (#320)

`0.15.0.0 <https://github.com/pypa/pipx/tree/0.15.0.0>`_
========================================================

Upgrade instructions: When upgrading to 0.15.0.0 or above from a pre-0.15.0.0 version, you must re-install all packages
to take advantage of the new persistent pipx metadata files introduced in this release. These metadata files store pip
specification values, injected packages, any custom pip arguments, and more in each main package's venv. You can do this
by running ``pipx reinstall-all`` or ``pipx uninstall-all``, then reinstalling manually.

- ``install`` now has no ``--spec`` option. You may specify any valid pip specification for ``install``'s main argument.
- ``inject`` will now accept pip specifications for dependency arguments
- Metadata is now stored for each application installed, including install options like ``--spec``, and injected
  packages. This information allows upgrade, upgrade-all and reinstall-all to work properly even with non-pypi installed
  packages. (#222)
- ``upgrade`` options ``--spec`` and ``--include-deps`` were removed. Pipx now uses the original options used to install
  each application instead. (#222)
- ``upgrade-all`` options ``--include-deps``, ``--system-site-packages``, ``--index-url``, ``--editable``, and
  ``--pip-args`` were removed. Pipx now uses the original options used to install each application instead. (#222)
- ``reinstall-all`` options ``--include-deps``, ``--system-site-packages``, ``--index-url``, ``--editable``, and
  ``--pip-args`` were removed. Pipx now uses the original options used to install each application instead. (#222)
- Handle missing interpreters more gracefully (#146)
- Change ``reinstall-all`` to use system python by default for apps. Now use ``--python`` option to specify a different
  python version.
- Remove the PYTHONPATH environment variable when executing any command to prevent conflicts between pipx dependencies
  and package dependencies when pipx is installed via homebrew. Homebrew can use PYTHONPATH manipulation instead of
  virtual environments. (#233)
- Add printed summary after successful call to ``pipx inject``
- Support associating apps with Python 3.5
- Improvements to animation status text
- Make ``--python`` argument in ``reinstall-all`` command optional
- Use threads on OS's without support for semaphores
- Stricter parsing when passing ``--`` argument as delimiter

`0.14.0.0 <https://github.com/pypa/pipx/tree/0.14.0.0>`_
========================================================

- Speed up operations by using shared venv for ``pip``, ``setuptools``, and ``wheel``. You can see more detail in the
  'how pipx works' section of the documentation. (#164, @pfmoore)
- Breaking change: for the ``inject`` command, change ``--include-binaries`` to ``--include-apps``
- Change all terminology from ``binary`` to ``app`` or ``application``
- Improve argument parsing for ``pipx run`` and ``pipx runpip``
- If ``--force`` is passed, remove existing files in PIPX_BIN_DIR
- Move animation to start of line, hide cursor when animating

`0.13.2.3 <https://github.com/pypa/pipx/tree/0.13.2.3>`_
========================================================

- Fix regression when installing a package that doesn't have any entry points

`0.13.2.2 <https://github.com/pypa/pipx/tree/0.13.2.2>`_
========================================================

- Remove unnecessary and sometimes incorrect check after ``pipx inject`` (#195)
- Make status text/animation reliably disappear before continuing
- Update animation symbols

`0.13.2.1 <https://github.com/pypa/pipx/tree/0.13.2.1>`_
========================================================

- Remove virtual environment if installation did not complete. For example, if it was interrupted by ctrl+c or if an
  exception occurred for any reason. (#193)

`0.13.2.0 <https://github.com/pypa/pipx/tree/0.13.2.0>`_
========================================================

- Add shell autocompletion. Also add ``pipx completions`` command to print instructions on how to add pipx completions
  to your shell.
- Un-deprecate ``ensurepath``. Use ``userpath`` internally instead of instructing users to run the ``userpath`` cli
  command.
- Improve detection of PIPX_BIN_DIR not being on PATH
- Improve error message when an existing symlink exists in PIPX_BIN_DIR and points to the wrong location
- Improve handling of unexpected files in PIPX_HOME (@uranusjr)
- swap out of order logic in order to correctly recommend --include-deps (@joshuarli)
- [dev] Migrate from tox to nox

`0.13.1.1 <https://github.com/pypa/pipx/tree/0.13.1.1>`_
========================================================

- Do not raise bare exception if no binaries found (#150)
- Update pipsi migration script

`0.13.1.0 <https://github.com/pypa/pipx/tree/0.13.1.0>`_
========================================================

- Deprecate ``ensurepath`` command. Use ``userpath append ~/.local/bin``
- Support redirects and proxies when downloading python files (i.e. ``pipx run http://url/file.py``)
- Use tox for document generation and CI testing (CI tests are now functional rather than static tests on style and
  formatting!)
- Use mkdocs for documentation
- Change default cache duration for ``pipx run`` from 2 to 14 days

`0.13.0.1 <https://github.com/pypa/pipx/tree/0.13.0.1>`_
========================================================

- Fix upgrade-all and reinstall-all regression

`0.13.0.0 <https://github.com/pypa/pipx/tree/0.13.0.0>`_
========================================================

- Add ``runpip`` command to run arbitrary pip commands in pipx-managed virtual environments
- Do not raise error when running ``pipx install PACKAGE`` and the package has already been installed by pipx (#125).
  This is the cause of the major version change from 0.12 to 0.13.
- Add ``--skip`` argument to ``upgrade-all`` and ``reinstall-all`` commands, to let the user skip particular packages

`0.12.3.3 <https://github.com/pypa/pipx/tree/0.12.3.3>`_
========================================================

- Update logic in determining a package's binaries during installation. This removes spurious binaries from the
  installation. (#104)
- Improve compatibility with Debian distributions by using ``shutil.which`` instead of
  ``distutils.spawn.find_executable`` (#102)

`0.12.3.2 <https://github.com/pypa/pipx/tree/0.12.3.2>`_
========================================================

- Fix infinite recursion error when installing package such as ``cloudtoken==0.1.84`` (#103)
- Fix windows type errors (#96, #98)

`0.12.3.1 <https://github.com/pypa/pipx/tree/0.12.3.1>`_
========================================================

- Fix "WindowsPath is not iterable" bug

`0.12.3.0 <https://github.com/pypa/pipx/tree/0.12.3.0>`_
========================================================

- Add ``--include-deps`` argument to include binaries of dependent packages when installing with pipx. This improves
  compatibility with packages that depend on other installed packages, such as ``jupyter``.
- Speed up ``pipx list`` output (by running multiple processes in parallel) and by collecting all metadata in a single
  subprocess call
- More aggressive cache directory removal when ``--no-cache`` is passed to ``pipx run``
- [dev] Move inline text passed to subprocess calls to their own files to enable autoformatting, linting, unit testing

`0.12.2.0 <https://github.com/pypa/pipx/tree/0.12.2.0>`_
========================================================

- Add support for PEP 582's ``__pypackages__`` (experimental). ``pipx run BINARY`` will first search in
  ``__pypackages__`` for binary, then fallback to installing from PyPI. ``pipx run --pypackages BINARY`` will raise an
  error if the binary is not found in ``__pypackages__``.
- Fix regression when installing with ``--editable`` flag (#93)
- [dev] improve unit tests

`0.12.1.0 <https://github.com/pypa/pipx/tree/0.12.1.0>`_
========================================================

- Cache and reuse temporary Virtual Environments created with ``pipx run`` (#61)
- Update binary discovery logic to find "scripts" like awscli (#91)
- Forward ``--pip-args`` to the pip upgrade command (previously the args were forwarded to install/upgrade commands for
  packages) (#77)
- When using environment variable PIPX_HOME, Virtual Environments will now be created at ``$PIPX_HOME/venvs`` rather
  than at ``$PIPX_HOME``.
- [dev] refactor into multiple files, add more unit tests

`0.12.0.4 <https://github.com/pypa/pipx/tree/0.12.0.4>`_
========================================================

- Fix parsing bug in pipx run

`0.12.0.3 <https://github.com/pypa/pipx/tree/0.12.0.3>`_
========================================================

- list python2 as supported language so that pip installs with python2 will no longer install the pipx on PyPI from the
  original pipx owner. Running pipx with python2 will fail, but at least it will not be as confusing as running the pipx
  package from the original owner.

`0.12.0.2 <https://github.com/pypa/pipx/tree/0.12.0.2>`_
========================================================

- forward arguments to run command correctly #90

`0.12.0.1 <https://github.com/pypa/pipx/tree/0.12.0.1>`_
========================================================

- stop using unverified context #89

`0.12.0.0 <https://github.com/pypa/pipx/tree/0.12.0.0>`_
========================================================

- Change installation instructions to use ``pipx`` PyPI name
- Add ``ensurepath`` command

`0.11.0.2 <https://github.com/pypa/pipx/tree/0.11.0.2>`_
========================================================

- add version argument parsing back in (fixes regression)

`0.11.0.1 <https://github.com/pypa/pipx/tree/0.11.0.1>`_
========================================================

- add version check, command check, fix printed version update installation instructions

`0.11.0.0 <https://github.com/pypa/pipx/tree/0.11.0.0>`_
========================================================

- Replace ``pipx BINARY`` with ``pipx run BINARY`` to run a binary in an ephemeral environment. This is a breaking API
  change so the major version has been incremented. (Issue #69)
- upgrade pip when upgrading packages (Issue #72)
- support --system-site-packages flag (Issue #64)

`0.10.4.1 <https://github.com/pypa/pipx/tree/0.10.4.1>`_
========================================================

- Fix version printed when ``pipx --version`` is run

`0.10.4.0 <https://github.com/pypa/pipx/tree/0.10.4.0>`_
========================================================

- Add --index-url, --editable, and --pip-args flags
- Updated README with pipsi migration instructions

`0.10.3.0 <https://github.com/pypa/pipx/tree/0.10.3.0>`_
========================================================

- Display python version in list
- Do not reinstall package if already installed (added ``--force`` flag to override)
- When upgrading all packages, print message only when package is updated
- Avoid accidental execution of ``pipx.__main__``
