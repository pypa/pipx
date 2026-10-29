###########
 Changelog
###########

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_, and this project adheres to `Semantic
Versioning <https://semver.org/spec/v2.0.0.html>`_.

Towncrier assembles released sections from ``changelog.d`` fragments. Pull request documentation builds show pending
fragments below; the tracked released history changes only when the release is prepared.

.. towncrier-draft-entries:: Unreleased

.. towncrier release notes start

.. _release-1-18-9:

`1.18.9 <https://github.com/pypa/pipx/tree/1.18.9>`_ - 2026-10-29
=================================================================

.. _release-1-18-9-fixed:

Fixed
-----

- Extend the 1.18.8 handling of recorded pip arguments to uv's path options and to ``--group``. pipx no longer records
  ``--group``, which names a ``pyproject.toml`` to read packages from, like ``-r``. On POSIX, a recorded
  ``--config-file``, ``--project``, ``--directory``, ``--overrides``/``--override`` or ``--excludes``/``--exclude`` that
  points at a path another account could change stops ``pipx upgrade``, ``pipx reinstall`` and the other replaying
  commands with the same error as ``--find-links``. ``pipx list --outdated`` runs the same check and reports such an
  environment as failed instead of querying the recorded location. ``pipx runpip`` reads its install arguments with the
  same parser, so it records an install written as ``-qe ./project`` or ``-e./project`` as editable (:pr:`2363`) by
  :user:`gaborbernat`.
- When a rebuild fails during a parallel ``pipx reinstall-all``, the restored environment gets back the shared app, man
  page or completion links another environment took while the rebuild had it in the trash, unless something outside this
  run has replaced them since (:pr:`2371`) by :user:`gaborbernat`.
- ``pipx run`` no longer reuses a cached environment after a change to a variable outside ``PIP_*`` and ``UV_*`` that
  decides which config file pip or uv reads, which proxy or index answers, which certificate is trusted or which
  credentials are sent, such as ``XDG_CONFIG_HOME``, ``SSL_CERT_FILE``, ``HTTPS_PROXY`` or ``NETRC``. The values only
  feed the cache key's hash, so secrets in them stay out of cache paths and logs (:pr:`2364`) by :user:`gaborbernat`.

.. _release-1-18-8:

`1.18.8 <https://github.com/pypa/pipx/tree/1.18.8>`_ - 2026-10-29
=================================================================

.. _release-1-18-8-fixed:

Fixed
-----

- A ``pipx run`` that names an app the package does not provide, such as ``pipx run --spec black blackk``, no longer
  expires the cached environment, so the corrected command reuses it instead of rebuilding. A failed venv creation or
  install still expires the entry (:pr:`2354`) by :user:`gaborbernat`.
- A second Ctrl-C during ``pipx reinstall-all``, ``upgrade-all`` or ``install-all`` no longer hangs pipx. A signal
  handled just after a worker took the shared lock could leave it held, so every other task waited forever (:pr:`2348`)
  by :user:`gaborbernat`.
- A self-managed pipx no longer adopts a recorded default interpreter that no longer backs its own environment, such as
  the ``python3`` of a bootstrap environment removed after ``pipx install pipx --python python3``. pipx failed every
  command with a ``PIPX_DEFAULT_PYTHON`` error, or built new environments on whatever appeared at that path later
  (:pr:`2245`) by :user:`gaborbernat`.
- Apply ``--cooldown`` and ``PIPX_COOLDOWN`` to the shared pip that the pip backend installs or refreshes during the
  command. pipx used to fetch the newest pip, even one uploaded minutes earlier, while it held back the package itself.
  A new shared environment now starts from the oldest pip pipx supports and upgrades only to a release older than the
  cooldown (:pr:`2311`) by :user:`gaborbernat`.
- Finish restoring an environment when Ctrl-C, ``SIGTERM`` or ``SIGHUP`` arrives while a failed or interrupted ``pipx
  reinstall``, ``install --force``, ``inject``, ``upgrade`` or ``manifest sync`` rolls it back. The rollback deletes the
  half-built environment and then moves the backup in, and a signal between the two steps left the environment deleted
  and its only copy in the trash, which the next pipx command emptied. pipx now holds such a signal until the backup is
  back in place and acts on it afterwards (:pr:`2329`) by :user:`gaborbernat`.
- For an editable install, pipx now copies only the man pages that resolve inside the project directory. Before, it
  followed absolute paths, ``..`` and symlinks, and a wheel installed by name could ship its own editable
  ``direct_url.json`` to make pipx copy any readable file into the environment and link it as a man page (:pr:`2268`) by
  :user:`gaborbernat`.
- Ignore apps, man pages and completions whose name is not a plain file name, such as ``..``, and never delete a
  directory to make room for an app link, so ``pipx reinstall`` can no longer remove the parent of ``PIPX_BIN_DIR``
  (:pr:`2228`) by :user:`gaborbernat`.
- Ignore recorded ``venv_args`` other than ``--system-site-packages``, with a warning, when reading a snapshot or
  ``pipx_metadata.json``, so ``pipx install-all`` and ``pipx reinstall`` no longer pass an edited ``--clear <dir>`` or
  an extra directory to ``python -m venv`` (:pr:`2239`) by :user:`gaborbernat`.
- Installing an editable project whose man page or project directory is a looping symlink no longer crashes pipx on
  Python 3.11 and 3.12; pipx skips that man page (:pr:`2334`) by :user:`gaborbernat`.
- Keep ``pipx reinstall-all``, ``upgrade-all``, and ``install-all`` waiting for the environments they change when pipx
  can no longer write their output, as with ``pipx reinstall-all 2>&1 | head`` or a closed stderr. pipx used to log a
  traceback and return while it still rebuilt environments in the background, so an interrupt then skipped the rollback,
  and an environment waiting for its turn hung (:pr:`2290`) by :user:`gaborbernat`.
- Keep a command, man page or completion link that another package took over while ``pipx reinstall``,
  ``reinstall-all``, ``uninject`` or ``uninstall-all`` was running. These commands gathered the environment's links
  first and deleted them by name later, so a name another package claimed in between, for example in the same parallel
  ``reinstall-all``, disappeared without a message. pipx now deletes a link only if it still points into the environment
  by Bernát Gábor.
- Keep pipx's ``pipx_metadata.json`` when the installer replaces it with a wheel's data file of the same name. A failed
  ``pipx install --force``, ``pipx upgrade`` or ``pipx inject``, or a ``pipx runpip APP install`` of a dependency, used
  to leave the wheel's copy in place, and later commands read its index arguments, spec and suffix as pipx's own. pipx
  now puts its record back after every installer run (:pr:`2269`) by :user:`gaborbernat`.
- Keep standalone Python archive members inside the unpack directory on Python 3.11.0 to 3.11.3, which lack
  ``tarfile.data_filter``. pipx's own extractor checked member names as text, so a member whose path went through a
  symlink unpacked earlier from the same archive was written wherever that link led. It now resolves each path through
  the links already on disk, extracts under normalized names like the data filter does, and refuses a hard link to a
  symlink (:pr:`2279`) by :user:`gaborbernat`.
- Keep the apps, manual pages, and completions of injected packages exposed when ``pipx manifest sync`` reinstalls an
  existing environment, and expose the environment again when the sync is interrupted. pipx used to drop those links
  without a message, so another package could take the freed names without ``--force``, and an interrupted sync left the
  rolled-back environment unexposed (:pr:`2273`) by :user:`gaborbernat`.
- Keep the environment when ``pipx install --force`` or ``pipx install-all --force`` cannot move it aside before a
  ``Requires-Python`` rebuild. On Windows the move fails while any file inside the environment is open, and pipx then
  deleted the environment and reported a ``FileNotFoundError`` instead of the real error. pipx now retries the move the
  way ``pipx reinstall`` does, and if it still fails it leaves the environment in place and reports the original error
  (:pr:`2350`) by :user:`gaborbernat`.
- Keep the recorded source of a local wheel when ``pipx runpip <venv> install`` abbreviates a value-taking pip option
  whose value names the package, such as ``--only-bin <name>`` for ``--only-binary <name>``, and record an install
  through an abbreviated ``--editable``, such as ``--edit <path>``, as editable (:pr:`2225`) by :user:`gaborbernat`.
- Keep the rollback backup of a running ``pipx reinstall``, ``reinstall-all``, ``install --force``, ``upgrade`` or
  ``inject`` when another pipx command starts. Every command used to empty the trash at startup, so a ``pipx list`` run
  meanwhile deleted the backup, and when the first command then failed or was interrupted it lost the environment with a
  ``FileNotFoundError``. pipx now skips a backup while its environment's lock is held and removes it only once orphaned
  (:pr:`2298`) by :user:`gaborbernat`.
- Leave a command, man page or completion that the environment did not expose before with its owner when ``pipx
  reinstall``, ``reinstall-all``, ``interpreter upgrade``, the repair step of ``pipx upgrade``, or a repeated ``pipx
  manifest sync`` rebuilds the environment. These used to replace such a file as if ``--force`` had been passed,
  deleting a user's own script or repointing another environment's command, although ``pipx install`` had left it alone
  with a warning. A name two environments both declare now stays with the one that held it, instead of going to
  whichever ``reinstall-all`` rebuilt last (:pr:`2321`) by :user:`gaborbernat`.
- Leave an existing environment alone in ``pipx install-all`` without ``--force``. pipx said it was not modifying the
  environment, then injected the snapshot's ``injected_packages`` into it anyway. Pass ``--force`` to bring existing
  environments in line with the snapshot (:pr:`2333`) by :user:`gaborbernat`.
- Let an environment take over an app, manual page, or completion name whose link points to a file that another
  installed environment no longer ships. pipx before 1.18.0 left such links behind when an upgrade dropped an app, and
  pipx kept them as collisions that only ``--force`` cleared. A link counts as left over when the environment it points
  into no longer lists the file in its metadata. The collision warning for a link whose target is missing now says so
  (:pr:`2356`) by :user:`gaborbernat`.
- Mask URL passwords and tokens in the remaining places that printed or logged them as typed: the ``Injecting packages``
  log line, the ``--output json`` error fields of ``inject``, ``install`` and ``uninject``, the progress lines of ``pipx
  run`` script dependencies and ``--preinstall``, the local source that ``pipx upgrade`` reports, invalid requirement
  errors from manifests and inline script metadata, ``--pip-args`` rejected by the uv backend of ``pipx run``, the
  "looks like a path" error, and installer output that pipx captures and logs (:pr:`2252`) by :user:`gaborbernat`.
- Mask a URL password that contains a literal space or tab, such as ``--index-url "http://alice:correct
  horse@host/simple"``, in the command log, ``--verbose`` output and messages; pipx now masks each argument of a command
  line before joining it (:pr:`2241`) by :user:`gaborbernat`.
- Mask the user part of URL credentials that contain a colon, so a token written as ``https://TOKEN:@host`` or
  ``TOKEN:x-oauth-basic@`` no longer shows in the command log, ``--verbose`` output and messages. Such URLs now show as
  ``****:****@``, which also hides a plain user name such as ``alice`` (:pr:`2244`) by :user:`gaborbernat`.
- On Windows under the uv backend, ``pipx run script.py`` now releases the run-cache lock before the script starts. pipx
  held it until the script exited, so a second run of the same script waited without a message, and a script that ran
  itself through pipx never finished (:pr:`2352`) by :user:`gaborbernat`.
- Refuse ``pipx install --lock`` and ``pipx manifest sync`` with a lock under the pip backend when the environment's pip
  is older than 26.1. That pip read ``pylock.toml`` as a requirements file: a real lock failed with a confusing
  ``Invalid requirement`` error, and a file that was not a lock had its lines applied as pip options. The error now
  names the pip version and suggests ``pipx upgrade-shared`` (:pr:`2289`) by :user:`gaborbernat`.
- Refuse a URL spec whose installed ``METADATA`` names a different project than its ``.dist-info`` directory. A wheel
  could rewrite that name through its data files and make ``pipx install --upgrade URL`` install it into another
  application's environment (:pr:`2236`) by :user:`gaborbernat`.
- Refuse a ``--python`` value that is not a version before ``--fetch-python=missing`` or ``--fetch-python=always`` looks
  in the standalone interpreter cache. pipx joined the raw value onto ``PIPX_HOME/py`` and deleted the result as a
  failed earlier download, so a directory path, ``..``, ``.`` or a bare ``python`` removed that directory, ``PIPX_HOME``
  or the whole interpreter cache (:pr:`2262`) by :user:`gaborbernat`.
- Refuse an empty or whitespace-only ``--index-url`` instead of silently installing from the default index (:pr:`2217`)
  by :user:`Svastikkka`.
- Refuse an empty or whitespace-only index option inside ``--pip-args`` (``--index-url``, ``-i``, ``--extra-index-url``,
  ``--default-index``, ``--index``), and under the uv backend an empty index recorded by an earlier install, instead of
  letting uv install from the default index (:pr:`2253`) by :user:`gaborbernat`.
- Refuse an environment name that is empty or a path instead of acting outside ``$PIPX_HOME/venvs``. ``pipx uninstall
  ""``, for example from an unset shell variable, used to remove every environment and exit 0, and an ``install-all``
  snapshot, manifest tool name or reported package name holding a path built the environment at that path. pipx now
  stops with ``Invalid environment name`` (:pr:`2331`) by :user:`gaborbernat`.
- Refuse to overwrite ``/etc/profile.d/pipx.sh`` or ``/etc/paths.d/pipx`` in ``pipx ensurepath --global`` when the file
  holds content pipx did not write, such as an administrator's ``PIPX_GLOBAL_HOME`` or ``PIP_INDEX_URL`` exports. pipx
  used to replace the whole file with its ``PATH`` entry and report success. It now leaves the file and its mode alone
  and exits with an error that names ``--force``, which still replaces the file. pipx replaces a file that holds only an
  earlier pipx entry, as before (:pr:`2315`) by :user:`gaborbernat`.
- Refuse to run ``pipx manifest lock`` when a tool's ``lock`` path resolves outside the manifest directory, instead of
  replacing a ``pylock.toml`` elsewhere on disk and discarding its previous contents. ``pipx manifest sync`` still reads
  such locks (:pr:`2223`) by :user:`gaborbernat`.
- Refuse to run pip or uv in an environment whose ``pyvenv.cfg`` is gone, and suggest ``pipx reinstall``. Without that
  file the environment's ``python`` link starts the interpreter it was created from, so a ``pipx upgrade`` after a wheel
  had shipped and then dropped ``pyvenv.cfg`` installed the package into that interpreter's prefix and reported success
  (:pr:`2326`) by :user:`gaborbernat`.
- Reject ``--global``, ``--skip-maintenance``, ``--verbose`` and ``--quiet`` placed between ``manifest``,
  ``interpreter`` or ``cache`` and their subcommand, as in ``pipx manifest --global sync``. pipx accepted the option
  there and then dropped it, so ``pipx manifest --global sync --prune`` synced and pruned the per-user store with exit
  0. Put the option after the subcommand, as in ``pipx manifest sync --global`` (:pr:`2320`) by :user:`gaborbernat`.
- Report an environment whose ``pipx_metadata.json`` the current user cannot read as unreadable in ``pipx list``,
  instead of as missing metadata from a pipx older than 0.15 that needs reinstalling. A non-root user sees this for
  every environment of ``pipx list --global``, because pipx keeps the file owner-only: it can hold index credentials.
  ``pipx list`` still lists the environments the user can read (:pr:`2323`) by :user:`gaborbernat`.
- Resolve every relative path given to a pip option, such as ``--cert ca.pem``, ``-r requirements.txt``, ``--log`` or
  ``--cache-dir``, against the directory pipx was started in, also when the option is clustered or abbreviated, as in
  ``-qr requirements.txt`` or ``--find-l wheels``. The shared pip refresh runs inside the shared libraries directory, so
  ``pipx upgrade-shared --pip-args='--cert=ca.pem'`` failed with ``invalid path: ca.pem``; installs, upgrades and ``pipx
  run`` now also resolve these values against the starting directory (:pr:`2351`) by :user:`gaborbernat`.
- Restore every earlier lock when ``pipx manifest lock`` fails because a directory sits at a later tool's lock path.
  pipx used to stop rolling back at that directory, keep the new locks of the tools before it, and delete their previous
  versions (:pr:`2260`) by :user:`gaborbernat`.
- Restore the existing environment when ``pipx install --force`` or ``pipx install-all --force`` rebuilds it on another
  interpreter because of the package's ``Requires-Python`` and the rebuild fails. pipx used to delete the environment
  first and leave behind an empty one without its app, injected packages, or ``pipx_metadata.json``, while it reported
  it had kept the environment. It now moves the environment to its trash before the rebuild and moves it back on failure
  (:pr:`2229`) by :user:`gaborbernat`.
- Stop ``pipx ensurepath --global --force`` from crashing with ``UnicodeDecodeError`` when ``/etc/profile.d/pipx.sh`` or
  ``/etc/paths.d/pipx`` holds bytes that are not UTF-8. ``--force`` now replaces the file without reading it, and
  without ``--force`` such a file gets the same error that names ``--force`` as any other file pipx did not write
  (:pr:`2355`) by :user:`gaborbernat`.
- Stop ``pipx interpreter upgrade`` from moving an environment to another Python found on ``PATH`` when the newest
  release of its package has a ``Requires-Python`` that rules out the new standalone build. The command reported the
  patch upgrade as done while the environment now ran on, for example, ``/usr/bin/python3.11``. It now fails, restores
  the environment on its standalone build, and exits 1 (:pr:`2301`) by :user:`gaborbernat`.
- Stop ``pipx upgrade-all`` from moving an app, manual page, or completion that two environments expose to the other
  environment while the installer of its owner is replacing the linked file. pipx treated any link whose target was
  missing as left over and replaced it without ``--force``; a missing target inside another environment that still
  exists now counts as a collision (:pr:`2303`) by :user:`gaborbernat`.
- Stop a self-managed pipx (``pipx install pipx``) started through its own environment's script from taking that
  environment's ``bin`` directory for ``PIPX_BIN_DIR`` when the path to the script holds ``..`` or a symlinked
  directory, such as ``../share/pipx/venvs/pipx/bin/pipx`` from ``~/.local/bin``. Such a command linked the apps it
  installed into pipx's own environment, off ``PATH`` and onto pipx's own import path. pipx now recognizes the exposed
  link by real locations, which also works when you reach the pipx home through a symlink (:pr:`2309`) by
  :user:`gaborbernat`.
- Stop pipx from importing modules out of the directory of its own launcher script, or out of the working directory
  under ``python -m pipx``, once ``pipx.__main__`` starts. After ``pip install --user pipx`` that directory is
  ``~/.local/bin``, where pipx links apps, so pipx imported a ``json.py`` or ``shlex.py`` script a package shipped there
  in place of the standard library module, and an exposed ``json.py`` broke every later pipx command, ``pipx uninstall``
  included. For modules pip's launcher imports before that point, such as ``re`` and ``enum``, pipx refuses to expose
  apps named after standard library modules. Programs that import ``pipx.__main__`` no longer see their script directory
  on ``sys.path`` either (:pr:`2316`) by :user:`gaborbernat`.
- Stop recording pip options that name a one-shot input or an output location, such as ``-r requirements.txt``,
  ``--log``, ``--report``, ``--cache-dir`` or ``--target``: they apply to the command they were given on, and a later
  ``pipx upgrade`` or ``pipx reinstall`` no longer reads or writes those paths. pipx reads pip arguments as pip does, so
  a clustered short option such as ``-qr requirements.txt`` or an abbreviation such as ``--log-f pip.log`` counts too.
  On POSIX, ``pipx upgrade``, ``pipx reinstall`` and the other commands that replay recorded arguments stop with an
  error, before the installer runs and without changing the record, when a recorded ``--find-links``, ``--constraint``,
  ``--build-constraint``, ``--cert``, ``--client-cert``, or ``file://`` or local-path index URL points at a path another
  account could change. Pass the options again with ``--pip-args`` to use them for that run (:pr:`2359`) by
  :user:`gaborbernat`.
- Stop two pipx commands that fetch the same standalone Python at once from leaving an interpreter with part of its
  standard library missing in ``PIPX_HOME/py``. Both staged the build in one fixed directory and each deleted the
  other's half-copied tree as a leftover; pipx now holds a per-version lock while it fetches, so the second command
  waits and reuses the first one's build. ``pipx interpreter list``, ``prune`` and ``upgrade`` also skip the staging and
  backup directories of a fetch in progress instead of treating them as interpreters. An interpreter that an earlier
  fetch already left incomplete still needs deleting by hand (:pr:`2293`) by :user:`gaborbernat`.
- The pip backend now removes ``pip.conf`` (``pip.ini`` on Windows) from the root of an environment before it starts pip
  there. A wheel could ship that file as a data file, and pip read it as its site configuration, so a ``target`` or
  index in it made a later ``pipx upgrade`` or ``pipx inject`` install outside the environment or from another index
  (:pr:`2264`) by :user:`gaborbernat`.
- Under the uv backend, ``--index-url`` (``-i``) now reaches uv as ``--default-index``. uv let ``UV_DEFAULT_INDEX`` or a
  default ``[[index]]`` entry override a command-line ``--index-url``, so ``pipx run``, ``install``, ``upgrade`` and
  ``outdated`` used the default index instead of the one named on the command line (:pr:`2247`) by :user:`gaborbernat`.
- Under the uv backend, ``pipx run script.py`` now keeps the script's environment in pipx's run cache, keyed to the
  script's path, the interpreter, ``--pip-args`` and the cooldown. uv kept one environment per script path and reused it
  while it satisfied the script, so a changed ``--index-url``, ``--pip-args`` or ``--cooldown``, or ``--refresh``, still
  ran what an earlier run installed. ``pipx cache purge`` and the 14-day expiry now cover these environments
  (:pr:`2274`) by :user:`gaborbernat`.
- Under the uv backend, ``pipx run`` now puts ``--`` before the app name it hands to ``uv tool run``. An app word that
  started with a single dash, such as ``pipx run -- -ihttp://host/simple demodep``, was read by uv as one of its own
  options, and uv installed and ran the next word as the package (:pr:`2299`) by :user:`gaborbernat`.
- Under the uv backend, ``pipx upgrade``, ``upgrade-all`` and ``install --upgrade`` now pass uv ``--upgrade-package
  NAME`` instead of ``--upgrade``, so they upgrade only the named package and leave its dependencies alone unless the
  new release needs others, as pip's default ``only-if-needed`` strategy does. Before, uv upgraded every dependency,
  replacing packages injected with ``pipx inject --force`` and pinned with ``pipx pin --injected-only`` (:pr:`2248`) by
  :user:`gaborbernat`.
- When ``pipx install`` or ``pipx run --spec`` under the pip backend has to install a URL, VCS or sdist spec to learn
  its name, the shared pip it installs along the way now comes from the command's ``--index-url`` and ``--pip-args``
  instead of pip's default index (:pr:`2275`) by :user:`gaborbernat`.
- When an environment holds two ``.dist-info`` records with the same name, pipx now reads the first one on ``sys.path``,
  the one the environment's interpreter uses. Since 1.15.1 it read the last one, so ``--system-site-packages`` with a
  different version of the package in the base interpreter reported that version and exposed its commands (:pr:`2258`)
  by :user:`gaborbernat`.
- ``pipx install --preinstall`` and ``pipx run --with`` now refuse a value that starts with ``-``. Written as
  ``--with=--find-links=DIR`` or ``--preinstall=-rFILE``, such a value reached pip or ``uv pip install`` as an installer
  option and changed where packages came from, instead of failing like the main package spec does. Pass installer
  options with ``--pip-args`` (:pr:`2307`) by :user:`gaborbernat`.
- ``pipx install-all --backend uv`` now translates index options that a pip recording spells as an abbreviation pip
  accepts, such as ``--index-u URL``, instead of dropping them and installing from the default index. A recorded pip
  ``--index URL`` now becomes uv ``--default-index URL``, matching how pip read it (:pr:`2232`) by :user:`gaborbernat`.
- ``pipx install`` with several packages no longer builds every environment on the Python it picked for one package
  whose ``Requires-Python`` rules out the default interpreter; the other packages keep the default Python (:pr:`2222`)
  by :user:`gaborbernat`.
- ``pipx list --outdated`` and ``pipx upgrade-all`` now check uv environments against the index recorded with uv's
  option names (``--default-index``, ``--index``, ``--allow-insecure-host``, ``--index-strategy``,
  ``--keyring-provider``) instead of uv's default index (:pr:`2220`) by :user:`gaborbernat`.
- ``pipx reinstall``, ``pipx reinstall-all`` and ``pipx repair`` now refuse an environment whose ``pipx_metadata.json``
  is unreadable or was lost to a killed install, instead of rebuilding it from the default index under the directory
  name. ``pipx install`` marks the environment unfinished until it writes the record, and ``pipx uninstall`` moves the
  environment to its trash before deleting it, so a killed uninstall no longer leaves a venv without its record
  (:pr:`2234`) by :user:`gaborbernat`.
- ``pipx run --with`` now installs the ``--with`` packages in the same installer call as the app. pipx skipped a
  ``--with`` naming a package the app already depends on, such as ``--with 'dep==1.0'``, as already installed, so the
  app ran with the newest release on the pip backend. A ``--with`` naming the app with an extra no longer links the
  cached environment's commands into ``PIPX_BIN_DIR`` (:pr:`2266`) by :user:`gaborbernat`.
- ``pipx run script.py`` now expires its cache entry when creating the environment fails or is interrupted, not only
  when installing the script's dependencies does. A Ctrl-C during ``python -m venv`` left an empty cache directory, and
  every later run of the script reused it and failed with ``FileNotFoundError`` until the entry expired (:pr:`2294`) by
  :user:`gaborbernat`.
- ``pipx run`` and ``pipx install`` now fail when a script download ends before its ``Content-Length``. Before, pipx ran
  or installed the part that arrived and could exit 0 (:pr:`2251`) by :user:`gaborbernat`.
- ``pipx run`` and ``pipx install`` now refuse an ``http`` or ``https`` script URL with credentials, naming it with the
  password masked. Before, a URL such as ``https://user:password@host/tool.py`` failed with an error that printed the
  password in clear text and wrote it to the log. ``pipx install`` also reports a malformed script URL as an error
  instead of a traceback (:pr:`2249`) by :user:`gaborbernat`.
- ``pipx run`` no longer keys its cache on the ``PIP_*`` and ``UV_*`` variables that cannot change what the installer
  resolves or installs: timeouts, retries, parallelism, verbosity, progress and color output, cache directories, and the
  ``UV_RUN_RECURSION_DEPTH`` that ``uv run`` sets for its children. Setting one of them rebuilt the environment for an
  unchanged command. Every other variable with those prefixes stays in the key, whatever its case or ``-``/``_``
  spelling, since pip reads ``PIP_index_url`` the same as ``PIP_INDEX_URL`` (:pr:`2353`) by :user:`gaborbernat`.
- ``pipx run`` now includes the installer's environment variables (``PIP_*``, or ``UV_*`` under the uv backend) in its
  cache key. A run after changing ``PIP_INDEX_URL``, ``PIP_FIND_LINKS`` or ``UV_INDEX_URL`` reused the environment built
  from the previous index for up to 14 days (:pr:`2282`) by :user:`gaborbernat`.
- ``pipx run`` now keys its cache on the absolute path of a local ``--spec``, ``--with`` or ``--find-links`` value. The
  same relative path typed in two directories, such as ``--spec ./dist/tool-1.0-py3-none-any.whl``, shared one
  environment, so the second directory ran the first directory's build by Bernát Gábor.
- ``pipx run`` now names the script URL, with credentials masked, when a download fails, as ``pipx install`` already
  did. ``pipx install`` of a script URL whose body does not decode in its declared charset, or declares an unknown one,
  now reports an error instead of a traceback, as ``pipx run`` already did (:pr:`2255`) by :user:`gaborbernat`.
- ``pipx runpip <venv> install`` now records a relative ``--find-links`` (``-f``) path resolved against the directory
  you ran it from. Before, a later ``pipx upgrade`` or ``pipx reinstall`` read it against the environment's directory,
  failed with ``Failed to read --find-links directory`` or ``No matching distribution found``, and rolled back
  (:pr:`2349`) by :user:`gaborbernat`.
- ``pipx runpip`` starts pip or uv in your working directory again instead of the environment's root, so relative paths
  such as ``-r requirements.txt``, ``-c constraints.txt`` or ``./dist/app.whl`` name your files. Since 1.12.0 the
  installer looked them up in the environment, where they were missing or named a data file an installed wheel had put
  there (:pr:`2318`) by :user:`gaborbernat`.
- ``pipx uninject`` no longer removes apps, man pages and completions that the main package or another injected package
  of the environment still exposes, such as a command of a dependency both packages share under ``--include-deps``
  (:pr:`2296`) by :user:`gaborbernat`.
- ``pipx uninject`` now ignores installed distributions whose metadata ``Name`` is not a valid project name when it
  looks for orphaned dependencies to remove. A name such as ``-t/some/dir`` or ``-rFILE`` reached ``uv pip uninstall``
  or ``pip uninstall`` as an option, and with uv could delete packages from a directory outside pipx (:pr:`2306`) by
  :user:`gaborbernat`.
- pipx no longer crashes on Python 3.11 and 3.12 when a package's ``installed-files.txt`` lists a looping symlink, and
  skips that entry instead (:pr:`2336`) by :user:`gaborbernat`.
- pipx no longer exposes an app whose name is a standard library module or ``pipx`` plus an import suffix, such as
  ``enum.py``, ``re.pyc`` or ``pipx.py``, or a directory named after one, and warns instead. Python searches the
  directory of the script it starts first, so in ``~/.local/bin`` such an app replaced the module for pip's ``pipx``
  launcher, which imports ``re`` and then ``pipx`` before pipx can drop that directory from ``sys.path``, and for every
  other Python script installed there (:pr:`2342`) by :user:`gaborbernat`.
- pipx no longer reads ``installed-files.txt`` from a distribution that has a ``RECORD``, matching
  ``importlib.metadata``. A dependency, or a package injected without ``--include-apps``, could ship that file into the
  main package's ``.dist-info`` and get its own apps, man pages and completions exposed without ``--include-deps``
  (:pr:`2277`) by :user:`gaborbernat`.
- pipx now adds ``-E`` to an app script's shebang by writing a new file and renaming it over the script, instead of
  writing into the existing file. With the uv backend the script can be a hard link or symlink into uv's cache, so the
  in-place write also changed the cache entry and the same script in every other environment uv had installed that wheel
  into (:pr:`2285`) by :user:`gaborbernat`.
- pipx now reads a package's ``entry_points.txt`` only when that package's ``RECORD`` lists it, or when the package has
  no ``RECORD``. A dependency could ship that file into the ``.dist-info`` of a main package that has no entry points of
  its own and get its apps exposed without ``--include-deps`` (:pr:`2340`) by :user:`gaborbernat`.

.. _release-1-18-8-documentation:

Documentation
-------------

- Document what the security policy covers: which inputs pipx trusts, and which reports count as vulnerabilities
  (:pr:`2198`) by :user:`gaborbernat`.

.. _release-1-18-8-security:

Security
--------

- A bare package name such as ``pipx install pycowsay`` now always means the package on the index. A file of that name
  without a suffix in the working directory no longer gets installed as a PEP 723 script; pass a path such as
  ``./pycowsay`` to install one. URL specs no longer pick up a script at the matching relative path below the working
  directory either (:pr:`2243`) by :user:`gaborbernat`.
- Ask the Python Launcher for Unix for a ``--python`` value only when it is an ``X`` or ``X.Y`` version. The launcher
  ran any other value, such as ``3.14.8`` or ``3.13t``, on the first interpreter its search found, which could be a
  ``.venv`` in a parent of the current directory (:pr:`2242`) by :user:`gaborbernat`.
- Create the self-managed bootstrap environment in the installation guide with ``mktemp -d`` instead of the fixed
  ``/tmp/bootstrap`` path, which another local user could create first and plant code in that ran as the reader, and as
  root at the ``sudo`` step (:pr:`2219`) by :user:`gaborbernat`.
- Look up a command name in ``PIPX_DEFAULT_PYTHON``, such as ``python3``, on ``PATH`` only: pipx no longer uses a file
  of that name in the current directory as the default interpreter. Write ``./python3`` to pick that file on purpose
  (:pr:`2226`) by :user:`gaborbernat`.
- Pass the absolute path ``PATH`` lookup found for ``--python python3.11`` on to the backend instead of the bare name.
  uv read the bare name as a version request and could pick a ``.venv`` interpreter from a parent of the current
  directory. A file in the current directory named like the value, such as ``./3.11``, no longer counts as a path either
  (:pr:`2240`) by :user:`gaborbernat`.
- Read a package name from a local ``pyproject.toml`` or wheel only for local path specs. A URL spec such as
  ``https://host/app.whl`` no longer takes its name, and with it the target environment, from a file at the matching
  relative path below the working directory (:pr:`2238`) by :user:`gaborbernat`.
- Record relative ``--find-links`` and ``--constraint`` values passed to ``pipx upgrade --pip-args`` and ``pipx run``
  scripts as absolute paths, resolve relative values already in ``pipx_metadata.json`` against the environment's
  directory, and run the shared pip refresh inside the shared libraries directory, so a later ``pipx upgrade`` or ``pipx
  reinstall`` no longer reads wheels from whatever directory you start it in (:pr:`2233`) by :user:`gaborbernat`.
- Record the index options of a ``pipx runpip <venv> install`` that replaces the main package, so a later ``pipx
  upgrade`` or ``pipx reinstall`` asks the same index instead of resolving the bare name on the default one (:pr:`2231`)
  by :user:`gaborbernat`.
- Start scripts read from a URL or a named pipe, ``pipx.run`` entry points, and apps run with ``--python-args`` with
  ``python -P`` so a module in the current directory, such as a planted ``json.py``, no longer shadows what the program
  imports (:pr:`2221`) by :user:`gaborbernat`.
- Stop ``pipx reinstall`` from replacing the main package while it replays injected packages. The replay passed
  ``--force-reinstall``, so an injected package that depends on the main package made the installer fetch the main
  package again by name from the injected package's index and install that release over the recorded source. ``pipx
  inject --force`` now passes ``--force-reinstall`` only when the package is already injected, and under the uv backend
  reinstalls just that package with ``--reinstall-package`` (:pr:`2227`) by :user:`gaborbernat`.
- Stop ``pipx run`` from retrying a failed uv install with pip. A venv directory without ``pipx_metadata.json`` no
  longer counts as recorded with the pip backend, so it resolves its backend like a new venv, and a ``pipx run`` whose
  install fails now expires its cache entry so the next run rebuilds it. pip ignores ``UV_INDEX_URL``, so the retry
  fetched the package from pip's default index instead of the private one (:pr:`2235`) by :user:`gaborbernat`.
- The uv backend no longer applies a ``uv.toml`` or ``pyproject.toml`` found in the directory uv runs in, the script's
  directory, or their parents, such as one another local account wrote to a shared ``/tmp``. pipx now points uv's
  project-config search at ``PIPX_HOME`` through ``UV_PROJECT``, and through ``--project`` for ``uv run --script``. Your
  user and system ``uv.toml`` and ``UV_CONFIG_FILE`` still apply. Keep ``PIPX_HOME`` out of directories other accounts
  can write (:pr:`2246`) by :user:`gaborbernat`.
- When ``pipx install --force`` or ``pipx manifest sync`` rebuilds an existing environment, either on another Python
  because the release's ``Requires-Python`` rules out the current one or to apply a lock file, keep the backend recorded
  for that environment. The rebuild used to pick the backend as for a new environment, so a pip-backed environment could
  move to uv and install from uv's default index instead of the one set in ``PIP_INDEX_URL`` or ``pip.conf``
  (:pr:`2237`) by :user:`gaborbernat`.
- ``pipx inject ENV 'APP[extra]'`` now adds the extra to the main package's recorded source instead of replacing it with
  the bare name ``APP[extra]``. An app installed from a wheel, a directory or a URL no longer turns into the index's
  project of the same name on the next ``pipx upgrade`` or ``pipx reinstall``. Extras accumulate with the ones already
  recorded, and a main-package spec that changes the version, path or URL needs ``--force`` (:pr:`2250`) by
  :user:`gaborbernat`.
- ``pipx manifest sync`` now keeps the installer and venv options recorded for an environment that already exists, such
  as ``--index-url``. It used to reinstall the tool from the default index and erase the recorded options (:pr:`2224`)
  by :user:`gaborbernat`.
- pipx now creates its log directory readable by its owner only (``0700``), tightens an existing one, and writes
  ``cmd_*.log`` and ``cmd_*_{pip,uv}_errors.log`` as ``0600``. The logs record the full command line, including the
  arguments ``pipx run`` and ``pipx exec`` pass to the application, and in a ``--global`` store under ``/opt/pipx/logs``
  any local account could read them (:pr:`2230`) by :user:`gaborbernat`.

.. _release-1-18-7:

`1.18.7 <https://github.com/pypa/pipx/tree/1.18.7>`_ - 2026-10-28
=================================================================

.. _release-1-18-7-security:

Security
--------

- Require pip 26.2.2 or later in the shared libraries, and replace an older shared pip on the next pipx command instead
  of waiting for the 30-day refresh. Older pip releases bundle a certifi that still trusts the compromised
  eMudhra/emSign root CA (:pr:`2197`) by :user:`gaborbernat`.

.. _release-1-18-6:

`1.18.6 <https://github.com/pypa/pipx/tree/1.18.6>`_ - 2026-10-28
=================================================================

.. _release-1-18-6-fixed:

Fixed
-----

- Keep the extras on a local archive named without ``./``, so ``pipx install "tool-1.0-py3-none-any.whl[cow]"`` installs
  the ``cow`` extra like ``./tool-1.0-py3-none-any.whl[cow]`` does. A version specifier, URL or environment marker after
  such a name now fails with an error instead of being silently dropped (:pr:`2174`) by :user:`Cyber-Marty` and
  :user:`gaborbernat`.
- Keep the recorded source of a local wheel when ``pipx runpip <venv> install`` passes an option value that names the
  package, such as ``--only-binary <name>``, ``--no-binary <name>``, or uv's ``--upgrade-package <name>`` (:pr:`2166`)
  by :user:`dailyun` and :user:`gaborbernat`.
- Read the full inline script metadata block when a TOML multiline string in it contains a ``# ///`` line, instead of
  failing with ``Unterminated string``. As the inline script metadata specification requires, the block now ends at the
  last ``# ///`` line of its comment run (:pr:`2172`) by :user:`zurrll` and :user:`gaborbernat`.
- Retain commands enabled by additional dependency extras with ``--include-deps`` (:pr:`2185`) by :user:`JackyHsu-X` and
  :user:`gaborbernat`.
- ``pipx install pkg-1.0.tar.xz`` and other bare filenames ending in an archive extension pip accepts (``.tar.bz2``,
  ``.tgz``, ``.tar`` and the rest, in any letter case) now install the local file instead of looking up a mangled
  project name on PyPI (:pr:`2177`) by :user:`ShahabAhmed01` and :user:`gaborbernat`.
- ``pipx upgrade-all --pip-args=--index-url``, or any other index option given without a value, now fails with an error
  naming the option instead of a ``StopIteration`` traceback, and ``--output json`` reports it in the usual error
  envelope (:pr:`2182`) by :user:`jdotc1` and :user:`gaborbernat`.

.. _release-1-18-6-documentation:

Documentation
-------------

- Fix the dead PythonBytes episode link on the docs home page (:pr:`2170`) by :user:`qodelicious` and
  :user:`gaborbernat`.
- Use a current black commit in the install-from-commit example (:pr:`2181`) by :user:`dcadolph` and
  :user:`gaborbernat`.

.. _release-1-18-5:

`1.18.5 <https://github.com/pypa/pipx/tree/1.18.5>`_ - 2026-10-27
=================================================================

.. _release-1-18-5-packaging:

Packaging
---------

- Releases now run on the shared tox-dev/github-workflows pipeline, with a locked release toolchain and generated GitHub
  Release notes (:pr:`2190`) by :user:`gaborbernat`.

.. _release-1-18-4:

`1.18.4 <https://github.com/pypa/pipx/tree/1.18.4>`_ - 2026-10-18
=================================================================

.. _release-1-18-4-fixed:

Fixed
-----

- `pipx reset` now cancels instead of crashing when the confirmation prompt reads EOF (Ctrl-D on POSIX, Ctrl-Z then
  Enter on Windows). (:pr:`2160`) by :user:`XXXXXQ-0206` and :user:`gaborbernat`

.. _release-1-18-3:

`1.18.3 <https://github.com/pypa/pipx/tree/1.18.3>`_ - 2026-10-17
=================================================================

.. _release-1-18-3-fixed:

Fixed
-----

- Allow selecting dependencies that ship only shell completions. (:pr:`2157`) by :user:`AryanRG` and :user:`gaborbernat`

.. _release-1-18-2:

`1.18.2 <https://github.com/pypa/pipx/tree/1.18.2>`_ - 2026-10-16
=================================================================

.. _release-1-18-2-fixed:

Fixed
-----

- Accept absolute `file:///` URLs as package specs, such as `pipx install file:///wheels/tool-1-py3-none-any.whl`.
  (:pr:`2150`) by :user:`srijan2607` and :user:`gaborbernat`
- In a terminal, show the pipx spinner again during installs and upgrades instead of the full `pip` or `uv` log, which
  `--verbose` still streams. Installer errors are still printed on failure. (:issue:`2151`)
- Print the installer error once when a `pipx upgrade --verbose` or pip `pipx install --verbose` fails, instead of
  repeating it after the live output. (:pr:`2153`) by :user:`gaborbernat`
- Stop an `-all` command on Ctrl-C even when the interpreter drops the interrupt, which happens when the signal handler
  runs inside a weakref callback or a finalizer. (:pr:`2154`) by :user:`gaborbernat`

.. _release-1-18-1:

`1.18.1 <https://github.com/pypa/pipx/tree/1.18.1>`_ - 2026-10-15
=================================================================

.. _release-1-18-1-fixed:

Fixed
-----

- Stop pip and uv when Ctrl-C lands early, instead of hanging. (:pr:`2146`) by :user:`gaborbernat`

.. _release-1-18-0:

`1.18.0 <https://github.com/pypa/pipx/tree/1.18.0>`_ - 2026-10-15
=================================================================

.. _release-1-18-0-added:

Added
-----

- Put `--suffix` last, except before a Windows file extension. Apps exposed by 1.17.14 keep their old name until pipx
  next exposes them, which renames them. (:pr:`2098`) by :user:`gaborbernat`
- `upgrade` and `reinstall-all` refresh shared pip only after 30 days. (:pr:`2116`) by :user:`gaborbernat`
- Run `pipx upgrade-shared` to refresh shared pip sooner. (:pr:`2116`) by :user:`gaborbernat`
- Set `PYTHON_LAZY_IMPORTS=normal` to opt out; the entry point is `pipx.__main__`. (:pr:`2132`) by :user:`gaborbernat`
- Defer every import, dependencies included, on Python 3.15 for faster startup. (:pr:`2132`) by :user:`gaborbernat`
- Run `reinstall-all`, `upgrade-all` and `install-all` across venvs at once. (:pr:`2137`) by :user:`gaborbernat`
- Let running upgrades finish on Ctrl-C in `upgrade-all`; a second Ctrl-C stops them, and the next `upgrade` repairs
  what was left half-upgraded. (:pr:`2144`) by :user:`gaborbernat`
- Retry uv-backend installs on a Python matching requires-python, as pip does. (:pr:`2144`) by :user:`gaborbernat`
- Translate recorded index options when `install-all --backend` switches between pip and uv. (:pr:`2144`) by
  :user:`gaborbernat`

.. _release-1-18-0-fixed:

Fixed
-----

- Warn that `--system-site-packages` is ignored by `inject` and `upgrade-all`. (:pr:`2089`) by :user:`gaborbernat`
- Fall back to pip with a warning when the auto-detected uv is older than 0.9.17. (:pr:`2092`) by :user:`gaborbernat`
- Use the default Python for scripts when it satisfies `requires-python`. (:pr:`2093`) by :user:`gaborbernat`
- Make `interpreter upgrade` move venvs off a patch-pinned standalone Python. (:pr:`2094`) by :user:`gaborbernat`
- Keep pins of injected packages through `reinstall`, `install-all` and `--force`. (:pr:`2095`) by :user:`gaborbernat`
- Restore recorded venv and pip args in `install-all` and reject bad spec files. (:pr:`2096`) by :user:`gaborbernat`
- Remove apps, man pages and completions an upgraded package no longer ships. (:pr:`2097`) by :user:`gaborbernat`
- Keep the interpreter on `install --force --python`. (:pr:`2098`) by :user:`gaborbernat`
- Make `pipx expose` relink resources missing after a collision or a deletion. (:pr:`2099`) by :user:`gaborbernat`
- Print only the envelope on `--output json` stdout and fix `health` JSON status. (:pr:`2101`) by :user:`gaborbernat`
- Keep users of a global pipx on their own paths and explain unwritable homes. (:pr:`2102`) by :user:`gaborbernat`
- Keep `PIPX_MAX_LOGS` logs, not one extra, and rotate uv error logs too. (:pr:`2103`) by :user:`gaborbernat`
- Keep the last output of a child process streamed to a terminal on macOS. (:pr:`2111`) by :user:`gaborbernat`
- Report apps whose Python is missing in `upgrade-all` instead of crashing. (:pr:`2141`) by :user:`gaborbernat`
- Show child output that is not valid UTF-8 instead of crashing. (:pr:`2144`) by :user:`gaborbernat`
- Mask passwords in index and package URLs in pipx's output and log files. (:pr:`2144`) by :user:`gaborbernat`

.. _release-1-18-0-performance:

Performance
-----------

- Read a local project's name from `pyproject.toml` instead of building it twice. (:pr:`2108`) by :user:`gaborbernat`
- Start every pipx command 50 to 130 ms faster by importing only what it uses. (:pr:`2113`) by :user:`gaborbernat`
- Create the shared libraries 35 to 50% faster by skipping a redundant pip run. (:pr:`2114`) by :user:`gaborbernat`
- Start half as many helper processes per install by reusing what pipx knows. (:pr:`2118`) by :user:`gaborbernat`
- Skip a WMI query on Windows at startup by detecting the OS with `sys.platform`. (:pr:`2125`) by :user:`gaborbernat`
- Uninject orphaned dependencies in one pip call, reported on one line. (:pr:`2126`) by :user:`gaborbernat`
- Check only pipx-managed packages for updates, not every installed dependency. (:pr:`2127`) by :user:`gaborbernat`
- Start pipx commands up to 30 ms faster by loading more modules on first use. (:pr:`2128`) by :user:`gaborbernat`
- Start pipx 10 to 50 ms faster on Python 3.15 through lazy imports. (:pr:`2129`) by :user:`gaborbernat`
- Check shared pip by its files instead of starting Python on every command. (:pr:`2131`) by :user:`gaborbernat`
- Read a local wheel's package name from its metadata instead of a probe venv. (:pr:`2134`) by :user:`gaborbernat`
- Scan exposed app and man page dirs once per `list` and `uninstall-all`. (:pr:`2138`) by :user:`gaborbernat`
- Require filelock 4.2, whose lighter import speeds up most pipx commands. (:pr:`2142`) by :user:`gaborbernat`

.. _release-1-18-0-documentation:

Documentation
-------------

- Correct the log directory in the platformdirs migration table. (:issue:`2086`)
- Correct docs that described pip-only behavior or outdated defaults and paths. (:pr:`2088`) by :user:`gaborbernat`
- Match help text, troubleshooting and samples to how pipx behaves today. (:pr:`2105`) by :user:`gaborbernat`

.. _release-1-17-14:

`1.17.14 <https://github.com/pypa/pipx/tree/1.17.14>`_ - 2026-10-12
===================================================================

.. _release-1-17-14-fixed:

Fixed
-----

- Build pipx wheels with Docutils 0.21.2 and later, including environments pinned to Docutils 0.22. (:pr:`2084`) by
  :user:`bfs2021` and :user:`gaborbernat`

.. _release-1-17-14-documentation:

Documentation
-------------

- Say that pipx rejects `--global` before the subcommand instead of ignoring it. (:pr:`2082`) by
  :user:`Ronak-Mahidharia` and :user:`gaborbernat`

.. _release-1-17-13:

`1.17.13 <https://github.com/pypa/pipx/tree/1.17.13>`_ - 2026-10-10
===================================================================

.. _release-1-17-13-fixed:

Fixed
-----

- Accept bare and suffixed injected package names in `pipx pin --skip`. (:pr:`2079`) by :user:`VedantBhayani` and
  :user:`gaborbernat`
- Use each snapshot's recorded interpreter when `pipx install-all` rebuilds an environment unless the user passes
  `--python`. (:pr:`2081`) by :user:`feiiiiii5` and :user:`gaborbernat`

.. _release-1-17-12:

`1.17.12 <https://github.com/pypa/pipx/tree/1.17.12>`_ - 2026-10-07
===================================================================

.. _release-1-17-12-fixed:

Fixed
-----

- Stop `pipx reinstall` from printing a traceback when the reinstall fails for an expected reason. (:pr:`2070`) by
  :user:`ParamTanna`
- Stop `pipx install` printing `WARNING: Skipping setuptools as it is not installed.` when the shared libraries are
  created on Python 3.12+, where setuptools is already absent. (:pr:`2071`) by :user:`officialpm` and
  :user:`gaborbernat`
- Stop an injected package in a suffixed environment from being renamed every time its record is rewritten: `pipx
  upgrade`, `pipx pin` and `pipx reinstall` no longer append the environment suffix again, so the package keeps its name
  in `pipx list --include-injected` and stays addressable by `pipx uninject`. (:pr:`2072`) by :user:`feiiiiii5` and
  :user:`gaborbernat`

.. _release-1-17-12-documentation:

Documentation
-------------

- Update the pipx logo author credit. (:issue:`2073`)

.. _release-1-17-11:

`1.17.11 <https://github.com/pypa/pipx/tree/1.17.11>`_ - 2026-10-03
===================================================================

.. _release-1-17-11-documentation:

Documentation
-------------

- Hide the extra documentation TOC toggle on narrow screens. (:issue:`2064`)

.. _release-1-17-10:

`1.17.10 <https://github.com/pypa/pipx/tree/1.17.10>`_ - 2026-10-02
===================================================================

.. _release-1-17-10-fixed:

Fixed
-----

- Remove an environment that has no pipx metadata and an interpreter that no longer runs, instead of crashing `pipx
  uninstall` and `pipx uninstall-all`. (:pr:`2059`) by :user:`hemcharan710-afk` and :user:`gaborbernat`
- Derive local script command names from the filename when parent directories contain `#`. A script installed by an
  earlier release under its directory's name no longer upgrades; uninstall it and install it again. (:issue:`2060`)
- Install a local PEP 723 script from its file when the path reads as a PyPI name (`pipx install bare.py`), contains
  `[`, or starts with a quoted `~`, and stop the upgrade hint from suggesting a PyPI reinstall for a script.
  (:pr:`2062`) by :user:`gaborbernat`

.. _release-1-17-9:

`1.17.9 <https://github.com/pypa/pipx/tree/1.17.9>`_ - 2026-10-01
=================================================================

.. _release-1-17-9-fixed:

Fixed
-----

- Stop adding ` -E` to an app script's shebang when the longer line would exceed the kernel's limit, which made the
  script fail on macOS with `Exec format error`. (:pr:`2058`) by :user:`feiiiiii5`, :user:`OpenCode` and
  :user:`gaborbernat`

.. _release-1-17-8:

`1.17.8 <https://github.com/pypa/pipx/tree/1.17.8>`_ - 2026-09-29
=================================================================

.. _release-1-17-8-fixed:

Fixed
-----

- Remove leftover shell completion scripts when running `pipx uninject`. (:issue:`2055`)

.. _release-1-17-7:

`1.17.7 <https://github.com/pypa/pipx/tree/1.17.7>`_ - 2026-09-28
=================================================================

.. _release-1-17-7-fixed:

Fixed
-----

- Prevent `pipx run` from sharing cached environments across different requirement lists or argument boundaries. This
  changes cache keys; run `pipx cache purge` to remove old entries. (:pr:`2053`) by :user:`januththedev` and
  :user:`gaborbernat`

.. _release-1-17-6:

`1.17.6 <https://github.com/pypa/pipx/tree/1.17.6>`_ - 2026-09-22
=================================================================

.. _release-1-17-6-fixed:

Fixed
-----

- Record each tool's dependency group as its lock's default so `pipx manifest sync` installs what `pipx manifest lock`
  wrote. Run `pipx manifest lock` again to fix existing locks. (:issue:`2049`)

.. _release-1-17-6-documentation:

Documentation
-------------

- Fix the argument order in the combined inject command example. (:pr:`2044`) by :user:`agammann`
- Use direct URL requirements for the Git install example with extras. (:issue:`2045`)

.. _release-1-17-5:

`1.17.5 <https://github.com/pypa/pipx/tree/1.17.5>`_ - 2026-09-20
=================================================================

.. _release-1-17-5-fixed:

Fixed
-----

- Report failed environments when running `pipx reinstall-all`. (:issue:`2042`)

.. _release-1-17-4:

`1.17.4 <https://github.com/pypa/pipx/tree/1.17.4>`_ - 2026-09-18
=================================================================

.. _release-1-17-4-fixed:

Fixed
-----

- `pipx upgrade` of a package installed from a local path, wheel, or VCS URL no longer reports "already at latest
  version". It now says the package is unchanged because it is installed from a local source and that no package index
  was checked, and suggests reinstalling by package name to track index releases. (:issue:`2040`)

.. _release-1-17-3:

`1.17.3 <https://github.com/pypa/pipx/tree/1.17.3>`_ - 2026-09-16
=================================================================

.. _release-1-17-3-fixed:

Fixed
-----

- Report a clear error when PIPX_MAX_LOGS is not a non-negative integer, instead of crashing on every pipx command.
  Empty or whitespace-only values fall back to the default everywhere, including log setup. (:pr:`2029`) by
  :user:`hktitof`
- Split `--pip-args` the way a shell would, so a quoted path with spaces such as `--find-links '/tmp/foo bar'` reaches
  pip intact instead of failing to parse. On Windows pipx now drops the quotes around each argument and keeps
  backslashes as path separators. (:pr:`2033`) by :user:`r3wretrhy`
- Stop `pipx runpip` from printing uv DEBUG logs on the uv backend. (:pr:`2035`) by :user:`anandghegde`

.. _release-1-17-3-documentation:

Documentation
-------------

- List every `--pip-args` flag the uv backend translates instead of only four. (:pr:`2037`) by :user:`hxperl` and
  :user:`claude`

.. _release-1-17-2:

`1.17.2 <https://github.com/pypa/pipx/tree/1.17.2>`_ - 2026-09-01
=================================================================

.. _release-1-17-2-fixed:

Fixed
-----

- Fix `KeyError` stderr noise when installing packages in Python3.15. (:pr:`2026`) by :user:`Cycloctane`

.. _release-1-17-1:

`1.17.1 <https://github.com/pypa/pipx/tree/1.17.1>`_ - 2026-08-30
=================================================================

.. _release-1-17-1-fixed:

Fixed
-----

- `pipx environment` now reports `PIPX_MAX_LOGS`, and `pipx environment --value PIPX_MAX_LOGS` no longer exits with
  `invalid choice`. (:pr:`2024`) by :user:`dylanpulver` and :user:`gaborbernat`

.. _release-1-17-0:

`1.17.0 <https://github.com/pypa/pipx/tree/1.17.0>`_ - 2026-08-29
=================================================================

.. _release-1-17-0-added:

Added
-----

- Add `PIPX_COOLDOWN`, a default for `--cooldown` on `install`, `install-all`, `inject`, `upgrade`, `upgrade-all` and
  `run`, so one release-age policy covers every command. An explicit `--cooldown` still wins, `--cooldown 0` opts a
  single command out, and a locked install ignores the variable rather than failing. (:issue:`2014`)

.. _release-1-17-0-fixed:

Fixed
-----

- Require `packaging>=26`. Earlier releases serialize a direct reference as `name@ url` rather than PEP 508's `name @
  url`, so the specifier pipx recorded in `pipx_metadata.json` and passed to the backend depended on which `packaging`
  happened to be installed. (:issue:`2015`)

.. _release-1-16-8:

`1.16.8 <https://github.com/pypa/pipx/tree/1.16.8>`_ - 2026-08-25
=================================================================

.. _release-1-16-8-fixed:

Fixed
-----

- `pipx run --spec <spec> <app>` on the uv backend builds a pipx-managed venv when `<app>` differs from the spec's
  normalized distribution name, or when the spec carries no name at all, so pipx honors the package's `[pipx.run]` entry
  point. An `<app>` that matches the name still runs through `uv tool run`, which sees console scripts only.
  (:issue:`2004`)

.. _release-1-16-8-documentation:

Documentation
-------------

- The CLI reference in the documentation now shows `pipx run` instead of `sphinx-build run`. (:issue:`2005`)

.. _release-1-16-7:

`1.16.7 <https://github.com/pypa/pipx/tree/1.16.7>`_ - 2026-08-13
=================================================================

.. _release-1-16-7-fixed:

Fixed
-----

- Fix pipx not being able to discover packages in separated platlib directories. (:pr:`1999`) by :user:`Cycloctane` and
  :user:`gaborbernat`
- Retry transient failures when fetching the python-build-standalone release index and downloading interpreter archives,
  resuming an interrupted archive download from the bytes already received instead of starting over. (:pr:`2001`) by
  :user:`gaborbernat`

.. _release-1-16-7-documentation:

Documentation
-------------

- Correct the documented Windows default for `PIPX_HOME`, which resolves to `%LOCALAPPDATA%\pipx\pipx` rather than
  `%LOCALAPPDATA%\pipx`. (:pr:`2002`) by :user:`aroh3006`

.. _release-1-16-6:

`1.16.6 <https://github.com/pypa/pipx/tree/1.16.6>`_ - 2026-08-04
=================================================================

.. _release-1-16-6-fixed:

Fixed
-----

- Stop appending a second `.exe` on Windows to the app name `pipx run` infers. (:issue:`1189`)
- Run the console script a package declares when `pipx run` infers the app name from a VCS URL, a local path, or a name
  it normalized, instead of passing a guess to `uv tool run`. Reusing that venv no longer reinstalls the package on
  every run. (:issue:`1994`)

.. _release-1-16-5:

`1.16.5 <https://github.com/pypa/pipx/tree/1.16.5>`_ - 2026-07-29
=================================================================

.. _release-1-16-5-fixed:

Fixed
-----

- Honor the version specifier when `pipx upgrade --install` installs a missing package. (:issue:`1987`)

.. _release-1-16-4:

`1.16.4 <https://github.com/pypa/pipx/tree/1.16.4>`_ - 2026-07-29
=================================================================

.. _release-1-16-4-fixed:

Fixed
-----

- Bundle `colorama` and `tomli` in the zipapp so the single `pipx.pyz` works on Windows and on Python 3.10.
  (:issue:`1978`, :issue:`1984`)
- Fix the Release Notes link published in package metadata. (:issue:`1980`)
- `PIPX_MAX_LOGS=0` now prunes the log files instead of keeping all of them. (:pr:`1988`) by :user:`marko1olo`

.. _release-1-16-4-documentation:

Documentation
-------------

- Fix the documentation links that 404 after the Sphinx move, including the PyPI Release Notes link. (:issue:`1980`)

.. _release-1-16-3:

`1.16.3 <https://github.com/pypa/pipx/tree/1.16.3>`_ - 2026-07-26
=================================================================

.. _release-1-16-3-fixed:

Fixed
-----

- Allow read-only global list commands when venv lock files are inaccessible. (:issue:`1974`)

.. _release-1-16-3-documentation:

Documentation
-------------

- Direct Linux users to PEP 668-compatible installation methods. (:issue:`1976`)

.. _release-1-16-2:

`1.16.2 <https://github.com/pypa/pipx/tree/1.16.2>`_ - 2026-07-21
=================================================================

.. _release-1-16-2-fixed:

Fixed
-----

- Stop venv inspection from crashing on Python 3.15 when a `dist-info` directory has no `Name` metadata field.
  `importlib.metadata` now raises `KeyError` for missing metadata keys instead of returning `None`; such distributions
  are skipped again, as on earlier Python versions. (:pr:`1971`) by :user:`gaborbernat`

.. _release-1-16-1:

`1.16.1 <https://github.com/pypa/pipx/tree/1.16.1>`_ - 2026-07-20
=================================================================

.. _release-1-16-1-fixed:

Fixed
-----

- Stop `install` and `list` from crashing when the pipx bin directory contains an executable pipx did not create.
  Scanning for launcher ownership decoded arbitrary binary content as an interpreter path, which raised
  `UnicodeDecodeError` on Windows, or `ValueError` for a path holding a NUL byte. Such a file is now treated as not
  owned by the venv. (:issue:`1965`)

.. _release-1-16-0:

`1.16.0 <https://github.com/pypa/pipx/tree/1.16.0>`_ - 2026-07-15
=================================================================

.. _release-1-16-0-added:

Added
-----

- Add `pipx list --outdated` and JSON output. (:issue:`149`)
- Honour the `requires-python` a package declares. When the default interpreter fails it, pipx looks for one on the
  system that satisfies it and builds the environment there, so `pipx install mytool` no longer needs the user to work
  out the right `--python`. Pass `--fetch-python=missing` to let pipx download a matching interpreter when the system
  carries none, and name `--python` yourself to keep the last word. (:issue:`387`)
- Normalize inferred `pipx run` package names. (:issue:`618`)
- Allow `pipx list` to select installed packages by name. (:issue:`640`)
- Add `--output` to structured commands. (:issue:`828`)
- Freeze the structured result envelope at `pipx_result_version` 1. Every `--output json` document now carries the
  command as a list of CLI tokens, a `status` of `success`, `partial`, or `error`, the process `exit_code`, the command
  `data`, and a top-level `errors` list whose entries each have a stable `code` and `message` alongside the
  `environment` and `package` they concern. A failure that stops a command before it builds a result renders the same
  envelope. (:issue:`828`)
- Add quiet and JSON output for package maintenance. (:issue:`828`)
- Give `pipx reinstall` and `pipx reinstall-all` the structured output the other commands carry. They printed straight
  to the terminal, so `--quiet` left `uninstalled NAME!` behind and no `--output json` existed to read the result from a
  script. Both now report through the shared renderer. (:issue:`828`)
- Give `pipx cache`, `pipx interpreter`, `pipx upgrade-shared`, `pipx manifest lock` and `pipx manifest sync` the
  structured output the other commands carry, so `--quiet` silences them and `--output json` hands a script the result.
  The `cache` and `interpreter` subcommands take `--quiet` and `--verbose` for the first time, since the shared options
  had passed them by. `pipx ensurepath` goes on printing its guidance, because its job is to tell a person what to add
  to a shell profile. (:issue:`828`)
- Add `--output json` to `pipx inject` and `pipx uninject`. (:issue:`828`)
- Infer the app name when running packages from VCS URLs. (:issue:`854`)
- Stream installer output during verbose installs. (:issue:`1069`)
- Draw the download progress bar of `pip` and `uv` during a plain `pipx install`, in place of the pipx spinner. pipx
  hands the installer a pseudo-terminal, which is the only way `uv` reports progress, and asks `uv` for its default
  output rather than the quiet one. A redirected stream keeps the previous behaviour. (:issue:`1069`)
- Allow commands to skip shared-library maintenance. (:issue:`1278`)
- Install PEP 723 scripts as persistent applications. (:issue:`1388`)
- Point library install errors to `inject` and `--preinstall`. (:issue:`1411`)
- Add commands to diagnose and repair broken environment interpreters. (:issue:`1442`)
- Add explicit tool manifests with separate PEP 751 locks. (:issue:`1506`)
- Add `pipx install --upgrade` to reconcile apps with package specs. (:issue:`1572`)
- Expose the shell completion scripts a package ships, the way pipx already exposes its man pages. A wheel that installs
  into `share/bash-completion/completions`, `share/zsh/site-functions` or `share/fish/vendor_completions.d` gets those
  files linked under `PIPX_COMPLETION_DIR`, which defaults to `~/.local/share`. `bash` and `fish` read those locations
  on their own; `zsh` needs the site-functions directory on its `fpath`. Uninstalling the package takes the links away.
  (:issue:`1604`)
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
- Default `PIPX_HOME` to the platform data directory on macOS and Windows again, which restores `~/Library/Application
  Support/pipx` on macOS. `platformdirs` reads `XDG_DATA_HOME` and `XDG_CACHE_HOME` on macOS, so exporting those moves
  the pipx directories. A pipx home from an earlier release keeps working as a fallback. (:issue:`1946`)
- Group the manifest commands under `pipx manifest`: use `pipx manifest lock` and `pipx manifest sync` in place of the
  top-level `pipx lock` and `pipx sync`. Keeping both verbs under one noun matches `pipx cache` and `pipx interpreter`
  and leaves the top-level command list about the manifest rather than two loose verbs.
- Keep `--json` only on `pipx list`, where it prints the versioned package snapshot that `install-all` reads back. Every
  other command dropped the `--json` alias in favour of `--output json`, so the snapshot format and the result envelope
  no longer share a flag.
- Name the existing-environment argument `ENVIRONMENT` across `inject`, `uninject`, `expose`, `unexpose`, `pin`,
  `unpin`, `uninstall`, `reinstall`, and `exec`, and fix the `uninject` help, which described the argument as the
  environment to inject into rather than uninject from.
- Record the interpreter and backend in the structured `install`, `upgrade`, and `upgrade-all` results, list
  `PIPX_GLOBAL_COMPLETION_DIR` in `pipx environment`, and show the shell-completion directory in `pipx list`.
  Completions had a global override that pipx honoured but never surfaced, and the records omitted which Python and
  backend produced a venv.
- Rename `--include-apps-from` to `--include-resources-from` and the manifest key to match. The option always exposed
  manual pages and shell completions alongside apps, so the new name describes what it does; `--include-apps` keeps its
  name. A venv recorded under the old key is migrated on read.
- Support standalone Python downloads on Windows ARM64. (:issue:`1856`)

.. _release-1-16-0-fixed:

Fixed
-----

- Check a candidate interpreter's real patch version against `requires-python`. pipx matched only on the minor version,
  so it rejected an installed `3.13.7` for `>=3.13.5` and accepted `3.14.6` for `<3.14.1`. It now queries each resolved
  interpreter and keeps the first whose full version satisfies the constraint. (:issue:`387`)
- Keep existing exposed files when copy-based environments provide the same resource name. (:issue:`540`)
- Recover custom paths when pipx manages its own installation on Unix. (:issue:`774`)
- Keep install failures in JSON with the correct environment. (:issue:`828`)
- Show injected apps in `pipx list` on systems that copy launchers. (:issue:`997`)
- Serialize shared-library maintenance across pipx processes. (:issue:`1056`)
- Wait for an installation before listing its environment. (:issue:`1056`)
- Draw the installer progress bar while the download runs. pipx reads the installer output over a pipe, which hid the
  terminal from `pip`, so `pip` held its bar back and printed a finished one once the download had ended.
  (:issue:`1069`)
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
- Avoid import crashes when stderr or its encoding is unavailable. (:issue:`1856`)
- Keep Windows uninject working while an exposed app runs. (:issue:`1856`)
- Translate pip binary and trusted-host options to valid uv run arguments, and reject `--no-deps` before invoking uv.
  (:issue:`1856`)
- Validate members before extracting a standalone Python archive on Python 3.10.0-3.10.11, which predate tarfile's data
  filter. pipx now refuses any entry whose path or link target would escape the download directory instead of falling
  back to an unfiltered extraction. (:issue:`1856`)
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
  pipx home that only exists for backwards compatibility. Setting `PIPX_HOME` still keeps both inside it.
  (:issue:`1946`)
- Retry fetching a standalone Python build when GitHub's release CDN returns a transient error, so a momentary `5xx` or
  rate-limit response no longer fails the install. (:pr:`1960`) by :user:`gaborbernat`
- Apply `pipx manifest lock` as all-or-nothing. When a manifest declares locks for several tools, pipx wrote the
  regenerated files one at a time, so a failure partway left some locks new and others old. Each target is now backed up
  before it is replaced and every applied lock is rolled back if any replacement fails.
- Apply a 30-second timeout and a 10 MiB size limit when downloading a remote `pipx run` or `pipx install` script, so a
  stalled or oversized URL can no longer hang pipx or exhaust memory. `pipx run` also accepts a script URL with a query
  string, such as `tool.py?raw=1`, by matching on the URL path.
- Honour a script's PEP 723 `requires-python` on the pip-backed `pipx run`. Without an explicit `--python`, pipx now
  picks an interpreter that satisfies the constraint, matching what the uv backend already does; with an explicit
  `--python` that fails the constraint it reports a clear error instead of running on an unsupported interpreter. A
  malformed inline metadata block now produces a readable message rather than a traceback.
- Include `pipx run --with` packages in the run-cache key. Because they were absent, `pipx run TOOL` and `pipx run
  --with EXTRA TOOL` shared one cached environment, so extras injected by one invocation leaked into later runs that
  asked for none. Each distinct set of extras now gets its own environment, and the extras are injected only when that
  environment is first built.
- Keep the backups that `install --force` and `reinstall` take while replacing an environment in pipx's trash rather
  than beside the live environments. A backup placed in the venvs directory was picked up as a broken environment by a
  concurrent `list` or `reinstall-all`; the trash shares the home's filesystem, so restoring a backup is still an atomic
  rename.
- Make a standalone Python upgrade atomic. pipx used to delete the existing interpreter before downloading its
  replacement, so a failed download or unpack left no interpreter at all. The new build is now staged beside the old one
  and swapped in only once it is complete, and a failed swap restores the previous build.
- Make the expired-cache sweep that runs before `pipx run` non-blocking. pipx used to wait for a lock on every other
  cached environment, so a concurrent `pipx run` whose install held one of those locks stalled the new run, a stall that
  lasted the whole install on Windows. The sweep now skips any environment another run is holding.
- Probe a `uv` found on `PATH` before using it, and bound every `uv --version` call with a timeout. A broken or hanging
  `uv` on `PATH` previously slipped past discovery and stalled the next command; pipx now skips such a binary and
  reports a clear error instead of hanging.
- Reject a `--suffix` that contains anything but letters, digits, and the characters `.` `_` `-` `+` `@`. A suffix is
  spliced straight into the names of the links pipx writes into `PIPX_BIN_DIR` and `PIPX_MAN_DIR`, so a value such as
  `/../../owned` could previously place those links outside pipx's own directories.
- Remove a dropped app or man page during upgrade only when pipx still owns the exposed file, so a command a user or
  another package replaced is left in place.
- Report `pipx expose` as a partial or failed operation when a resource cannot be linked because a foreign file already
  occupies its target name. The command previously claimed success while silently leaving those apps or manual pages
  unexposed; it now lists each conflict in the structured result and exits non-zero.
- Stop forcing `UV_NO_PROGRESS=1` on every uv call. The override silenced uv's progress bar even when pipx asked to draw
  one, and it ignored a `UV_NO_PROGRESS` already set in the environment. pipx now suppresses the bar only in quiet,
  JSON, and non-interactive runs, and defers to the caller's `UV_NO_PROGRESS` when it does want progress shown.
- Track exposed shell completions through the full environment lifecycle. Stale-resource cleanup during install,
  upgrade, and reinstall, the repair relink check, and the ownership filter now include completions alongside apps and
  manual pages, so a completion a package stops shipping is removed instead of lingering.

.. _release-1-16-0-performance:

Performance
-----------

- Check upgrades in parallel and skip installs for current packages. (:issue:`1353`)
- Index installed distributions during environment inspection. (:issue:`1856`)
- Cache each managed environment's site-packages path. (:issue:`1856`)
- Read environment metadata once per interpreter upgrade. (:issue:`1856`)
- Cache shared-library validity checks within each pipx process. (:issue:`1856`)
- List managed environments only when shell completion requests them. (:issue:`1856`)
- Cache resolved pipx context paths. (:issue:`1856`)
- Compute only the requested `pipx environment --value` entry. (:issue:`1856`)
- Reuse the `pipx run` PATH lookup when warning about an existing app. (:issue:`1856`)
- Resolve the default Python interpreter on first use instead of import. (:issue:`1856`)
- Inspect legacy environments once during uninstall and reinstall. (:issue:`1856`)

.. _release-1-16-0-documentation:

Documentation
-------------

- Document the pipx application scope and feature boundaries. (:issue:`177`)

.. _release-1-16-0-removed:

Removed
-------

- Remove the `PIPX_HOME_ALLOW_SPACE` environment variable and the warning about spaces in the pipx home path. `pip` and
  `uv` both write a `/bin/sh` wrapper as the shebang when the interpreter path contains a space, so applications
  installed into such a path run. (:issue:`1946`)

.. _release-1-15-2:

`1.15.2 <https://github.com/pypa/pipx/tree/1.15.2>`_ - 2026-07-15
=================================================================

.. _release-1-15-1:

`1.15.1 <https://github.com/pypa/pipx/tree/1.15.1>`_ - 2026-07-15
=================================================================

.. _release-1-15-1-fixed:

Fixed
-----

- Retry fetching a standalone Python build when GitHub's release CDN returns a transient error, so a momentary ``5xx``
  or rate-limit response no longer fails the install. (:pr:`1960`) by :user:`gaborbernat`

.. _release-1-15-0:

`1.15.0 <https://github.com/pypa/pipx/tree/1.15.0>`_ - 2026-06-24
=================================================================

.. _release-1-15-0-added:

Added
-----

- Add a ``--dry-run`` flag to ``pipx ensurepath`` that reports which directories would be added to ``PATH`` without
  modifying ``PATH`` or any shell configuration file. (:issue:`1014`)

.. _release-1-15-0-fixed:

Fixed
-----

- Fix ``pipx uninject`` for uv-backed environments, where uv lacks pip's ``list --not-required`` option. Both backends
  now derive the not-required set from installed distribution metadata, so they behave identically, and a dependency
  pulled in only by another package's extra is kept instead of being treated as removable. (:issue:`1841`)

.. _release-1-14-1:

`1.14.1 <https://github.com/pypa/pipx/tree/1.14.1>`_ - 2026-06-17
=================================================================

.. _release-1-14-1-fixed:

Fixed
-----

- Restore the original package if ``pipx reinstall-all`` is interrupted during reinstall. (:issue:`966`)
- Allow importing ``pipx.util`` before ``pipx.paths``. (:issue:`1333`)
- Ensure ``pipx inject --force`` reinstalls injected packages without persisting the force-reinstall option in package
  metadata. (:issue:`1545`)
- Preserve installer errors when package-name detection fails during local package installs. (:issue:`1567`)
- Expose manual pages for editable local package installs. (:issue:`1793`)
- Fixed ``pipx pin <app> --injected-only`` so it can pin injected packages when the main app is already pinned.
  (:pr:`1835`) by :user:`marko1olo`

.. _release-1-14-0:

`1.14.0 <https://github.com/pypa/pipx/tree/1.14.0>`_ - 2026-06-04
=================================================================

.. _release-1-14-0-added:

Added
-----

- Add ``--no-path-check`` to ``pipx run`` to skip the warning when the app is already on ``PATH``. Useful for shim
  scripts that wrap ``pipx run <app>`` under the same name as the app. (:issue:`1824`)

.. _release-1-14-0-documentation:

Documentation
-------------

- Use the bootstrap pipx executable when adding PATH in self-managed installs. (:issue:`1481`)

.. _release-1-13-0:

`1.13.0 <https://github.com/pypa/pipx/tree/1.13.0>`_ - 2026-05-30
=================================================================

.. _release-1-13-0-added:

Added
-----

- Add ``PIPX_DISABLE_SHARED_LIBS_AUTO_UPGRADE`` to skip automatic shared library upgrades. (:issue:`1650`)
- Update the error message in get-pipx.py; it is obsoleted, not deprecated. (:pr:`1813`) by :user:`Spitfire1900`

.. _release-1-13-0-fixed:

Fixed
-----

- Install app scripts with shebangs that ignore ``PYTHONPATH``. (:issue:`1584`)
- Refresh cached standalone Python indexes written by older pipx versions before using ``--fetch-missing-python``.
  (:issue:`1774`)

.. _release-1-13-0-documentation:

Documentation
-------------

- Document how to clear cache warnings from ``runpip``. (:issue:`1802`)

.. _release-1-12-0:

`1.12.0 <https://github.com/pypa/pipx/tree/1.12.0>`_ - 2026-05-06
=================================================================

.. _release-1-12-0-added:

Added
-----

- Add ``--fetch-python`` and ``PIPX_FETCH_PYTHON`` to control standalone Python downloads, with values ``always``,
  ``missing``, or ``never``. (:pr:`1663`) by :user:`13steinj` and :user:`gaborbernat`
- Add an opt-in ``uv`` backend. Install ``pipx[uv]`` (or put ``uv`` on ``PATH``) and pipx will create venvs with ``uv
  venv``, manage packages with ``uv pip``, and run ephemeral apps via ``uv tool run``.

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

.. _release-1-12-0-deprecated:

Deprecated
----------

- Deprecate ``--fetch-missing-python`` and ``PIPX_FETCH_MISSING_PYTHON``; both are now aliases for
  ``--fetch-python=missing`` / ``PIPX_FETCH_PYTHON=missing``. ``PIPX_FETCH_MISSING_PYTHON=0`` (and other falsy values)
  now disables fetching, where previously any value enabled it. The ``pipx.interpreter.find_python_interpreter`` keyword
  ``fetch_missing_python: bool`` is replaced by ``fetch_python: FetchPythonOptions``. (:pr:`1663`) by :user:`13steinj`
  and :user:`gaborbernat`

.. _release-1-11-2:

`1.11.2 <https://github.com/pypa/pipx/tree/1.11.2>`_ - 2026-05-05
=================================================================

.. _release-1-11-2-added:

Added
-----

- Add ``pipx help`` and ``pipx help <command>`` aliases for existing help output. (:issue:`1535`)
- Drop support for Python 3.9. (:pr:`1786`) by :user:`henryiii`
- Replace if/elif command dispatch in main.py with argparse set_defaults. (:issue:`1794`)

.. _release-1-11-1:

`1.11.1 <https://github.com/pypa/pipx/tree/1.11.1>`_ - 2026-03-31
=================================================================

.. _release-1-11-1-fixed:

Fixed
-----

- Ignore ``PIP_TARGET`` environment variable to prevent pip from installing outside the venv. (:issue:`735`)
- Fix ``pipx install`` failing on Windows when the username contains non-Latin characters (e.g. cyrillic, Chinese).
  (:issue:`780`)
- Show installed version and suggest ``upgrade`` when ``install`` detects an existing installation. (:issue:`795`)
- ``--verbose`` and ``--quiet`` flags before the subcommand are no longer silently ignored. (:issue:`1282`)
- Remove dependency app symlinks when uninjecting a package that was injected with ``--include-deps``. (:issue:`1364`)
- Remove ``setuptools`` from shared libs to prevent version conflicts when app venvs use a different Python.
  (:issue:`1539`)
- Prevent ``uninject`` from removing dependencies still needed by other packages in the venv. (:issue:`1672`)

.. _release-1-11-0:

`1.11.0 <https://github.com/pypa/pipx/tree/1.11.0>`_ - 2026-03-23
=================================================================

.. _release-1-11-0-added:

Added
-----

- Add ``PIPX_MAX_LOGS`` environment variable to configure the maximum number of log files to keep. (:issue:`1570`)

.. _release-1-11-0-fixed:

Fixed
-----

- Allow ``--pip-args`` to be passed to ``upgrade-all``. (:issue:`1503`)
- Fix ``--pip-args='-c <url>'`` breaking when constraint target is a URL instead of a local path. (:issue:`1582`)
- Enable keyring authentication for private package indexes by setting ``PIP_KEYRING_PROVIDER=subprocess``
  (:issue:`1603`)
- Added error handling for ``pip list`` command failures (:issue:`1698`)

.. _release-1-11-0-documentation:

Documentation
-------------

- Remove outdated "experimental" note from ``--suffix`` help text. (:issue:`1621`)

.. _release-1-10-1:

`1.10.1 <https://github.com/pypa/pipx/tree/1.10.1>`_ - 2026-03-20
=================================================================

.. _release-1-10-1-fixed:

Fixed
-----

- Use stored pip_args from install metadata when running ``pipx upgrade`` without explicit ``--pip-args``
  (:issue:`1441`)
- Fix ``--global`` flag being silently ignored when placed before the subcommand (:issue:`1443`)
- Respect ``--quiet`` flag in ``install`` and suppress animations and success messages (:issue:`1508`)
- Catch missing Python interpreter in ``upgrade`` and show helpful error instead of crashing (:issue:`1602`)
- Prevent data loss by rejecting relative paths in ``uninstall``, ``reinstall``, and other package-name arguments
  (:issue:`1718`)

.. _release-1-10-0:

`1.10.0 <https://github.com/pypa/pipx/tree/1.10.0>`_ - 2026-03-18
=================================================================

.. _release-1-10-0-added:

Added
-----

- Add ``--with`` flag to ``pipx run`` to allow injecting dependencies (:issue:`1607`)
- add more specific directions in the logs towards a resolution if you have a space in the PIX_HOME path (:issue:`1634`)

.. _release-1-10-0-fixed:

Fixed
-----

- Fixed upgrade command failing when package name includes extras (e.g., ``pipx upgrade "coverage[toml]"``).
  (:issue:`925`)
- Fix run command with bash substitution (e.g. ``pipx run <(pbpaste)``) (:issue:`1293`)
- Allow ``pipx runpip`` to split single string arguments. (:issue:`1520`)
- Fix handling of shared libraries when the original Python interpreter is removed on Windows by detecting stale venv
  references and recreating the shared libraries with the current Python. (:issue:`1723`)

.. _release-1-9-0:

`1.9.0 <https://github.com/pypa/pipx/tree/1.9.0>`_ - 2026-03-17
===============================================================

.. _release-1-9-0-added:

Added
-----

- Add completion choices for ``pipx environment --value``. (:issue:`1498`)

.. _release-1-9-0-fixed:

Fixed
-----

- Ignore recursive symlink loops in PIPX_BIN_DIR. (:issue:`1592`)
- ``pipx reinstall``: An exception will now be raised if package is pinned. (:issue:`1611`)
- Stop ``pipx run`` from leaving bad temporary venvs when first installation was unsuccessful. (:issue:`1709`)

.. _release-1-8-0:

`1.8.0 <https://github.com/pypa/pipx/tree/1.8.0>`_ - 2025-09-30
===============================================================

.. _release-1-8-0-added:

Added
-----

- Rename environmental variable ``USE_EMOJI`` to ``PIPX_USE_EMOJI``. (:issue:`1395`)
- Add ``--all-shells`` flag to ``pipx ensurepath``. (:issue:`1585`)
- Add support for Python 3.13 (:pr:`1647`) by :user:`dukecat0`

.. _release-1-8-0-fixed:

Fixed
-----

- On Windows, no longer overwrite existing files on upgrade if source and destination are the same (:issue:`683`)
- Update the logic of finding python interpreter such that ``--fetch-missing-python`` works on Windows (:issue:`1521`)
- Fix no message displayed when no packages are upgraded with ``upgrade-all``. (:issue:`1565`)
- Fix incorrect order of flags when using ``pipx upgrade``. (:issue:`1610`)
- Update the archive name of build of Python for Windows (:issue:`1630`)
- Set up standalone python fetching to use checksums directly from the GitHub API. (:issue:`1652`)
- Fix running a script with explicitly empty ``dependencies = []``. (:pr:`1658`) by :user:`neutrinoceros`

.. _release-1-8-0-documentation:

Documentation
-------------

- Fix ``/changelog/`` and ``/contributing/`` docs URLs (:issue:`1540`)

.. _release-1-7-1:

`1.7.1 <https://github.com/pypa/pipx/tree/1.7.1>`_ - 2024-08-23
===============================================================

.. _release-1-7-1-fixed:

Fixed
-----

- Use minimum supported Python to build zipapp in release action such that ``tomli`` is included in it. (:issue:`1514`)

.. _release-1-7-0:

`1.7.0 <https://github.com/pypa/pipx/tree/1.7.0>`_ - 2024-08-22
===============================================================

.. _release-1-7-0-added:

Added
-----

- Add a ``--prepend`` option to the ``pipx ensurepath`` command to allow prepending ``pipx``'s location to ``PATH``
  rather than appending to it. This is useful when you want to prioritize ``pipx``'s executables over other executables
  in your ``PATH``. (:pr:`1451`) by :user:`agriyakhetarpal` and :user:`Gitznik`
- List ``PIPX_GLOBAL_[HOME|BIN_DIR|MAN_DIR]`` in ``pipx environment``. (:issue:`1492`)
- Introduce ``PIPX_HOME_ALLOW_SPACE`` environment variable, to silence the spaces in pipx home path warning
  (:issue:`1320`)

.. _release-1-7-0-fixed:

Fixed
-----

- Fix passing constraints file path into ``pipx install`` operation via ``pip`` args (:issue:`1389`)
- Stop ``pipx install --global`` from installing files in ``~/.local``. (:issue:`1475`)
- Fix installation abortion on multiple packages when one or more are already installed. (:issue:`1509`)

.. _release-1-7-0-documentation:

Documentation
-------------

- Add help messages for ``pipx pin`` and ``pipx unpin`` commands. (:pr:`1438`) by :user:`dukecat0`
- Move all documentation files to the ``docs`` directory. (:issue:`1479`)

.. _release-1-6-0:

`1.6.0 <https://github.com/pypa/pipx/tree/1.6.0>`_ - 2024-06-01
===============================================================

.. _release-1-6-0-added:

Added
-----

- Add ``install-all`` command to install packages according to spec metadata file. (:issue:`687`)
- Introduce ``pipx pin`` and ``pipx unpin`` commands, which can be used to pin or unpin the version of an installed
  package, so it will not be upgraded by ``pipx upgrade`` or ``pipx upgrade-all``. (:issue:`891`)
- Add a new option ``--pinned`` to ``pipx list`` command for listing pinned packages only. (:issue:`891`)
- Add ``pipx interpreter upgrade`` command to upgrade local standalone python in micro/patch level (:issue:`1249`)
- Add ``--requirement`` option to ``inject`` command to read list of packages from a text file. (:pr:`1252`) by
  :user:`jamesmyatt`, :user:`chrysle` and :user:`huxuan`
- Add ``pipx upgrade-shared`` command, to create/upgrade shared libraries as a standalone command. (:pr:`1316`) by
  :user:`mayeut` and :user:`chrysle`
- Allow ``upgrade`` command to accept multiple packages as arguments. (:issue:`1336`)
- Support Python version for ``--python`` arg when py launcher is not available (:issue:`1342`)
- Make ``install-all`` gather errors in batch (:pr:`1348`) by :user:`huxuan`, :user:`dukecat0` and :user:`chrysle`
- Support python3.8 for standalone python builds (:issue:`1375`)

.. _release-1-6-0-fixed:

Fixed
-----

- Resolve the ``DEFAULT_PYTHON`` to the actual absolute path (:issue:`965`)
- Fix error log overwrite for "-all" batch operations. (:issue:`1132`)
- Do not reinstall already injected packages without ``--force`` being passed. (:issue:`1300`)
- Only show ``--python`` and ``--force`` flag warning if both flags are present (:issue:`1304`)
- Don't allow paths to be passed into ``pipx reinstall``, as this might wreak havoc. (:issue:`1324`)
- Make the Python ``venv`` module arguments work with ``upgrade --install`` (:issue:`1344`)
- Fix version check for standalone python (:issue:`1349`)
- Validate package(s) argument should not be path(s). (:issue:`1354`)
- Validate whether a package is an URL correctly. (:issue:`1355`)
- Install specified version of ``--preinstall`` dependency instead of latest version (:issue:`1377`)
- Move ``--global`` option into shared parser, such that it can be passed after the subcommand, for example ``pipx
  ensurepath --global``. (:pr:`1397`) by :user:`dukecat0`
- Fix discovery of a ``pipx run`` entry point if a local path was given as package. (:pr:`1422`) by :user:`chrysle` and
  :user:`huxuan`

.. _release-1-6-0-documentation:

Documentation
-------------

- Create a dedicated section for manual pages and add an example with ``pdm-backend``. (:pr:`1312`) by :user:`pawamoy`
- Add example, test and cli help description how to install multiple packages with the --preinstall flag (:pr:`1321`) by
  :user:`gempir`
- Refine docs generation script and template. (:issue:`1325`)
- Add a note about sourcing the shell config file for ``ensure_path`` (:issue:`1346`)

.. _release-1-5-0:

`1.5.0 <https://github.com/pypa/pipx/tree/1.5.0>`_ - 2024-03-29
===============================================================

.. _release-1-5-0-added:

Added
-----

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

.. _release-1-5-0-fixed:

Fixed
-----

- Correctly resolve home directory in pipx directory environment variables. (:issue:`94`)
- Pass through ``pip`` arguments when upgrading shared libraries. (:issue:`964`)
- Fix installation issues when files in the working directory interfere with venv creation process. (:issue:`1091`)
- Report correct filename in tracebacks with ``pipx run <scriptname>`` (:pr:`1191`) by :user:`henryiii` and
  :user:`flying-sheep`
- Let self-managed pipx uninstall itself on windows again. (:issue:`1203`)
- Fix path resolution for python executables looked up in PATH on windows. (:issue:`1205`)
- Display help message when ``pipx install`` is run without arguments. (:pr:`1266`) by :user:`dukecat0`
- Fix crashes due to superfluous ``-q`` flags by discarding exceeding values (:issue:`1283`)

.. _release-1-5-0-documentation:

Documentation
-------------

- Update the completion instructions for zipapp users. (:issue:`1072`)
- Update the example for running scripts with dependencies. (:issue:`1227`)
- Update the docs for package developers on the use of configuration using pyproject.toml (:issue:`1229`)
- Add installation instructions for Fedora (:pr:`1239`) by :user:`markmc`
- Update the examples for installation from local dir (:issue:`1277`)
- Fix inconsistent wording in ``pipx install`` command description. (:pr:`1307`) by :user:`sgryjp`

.. _release-1-5-0-deprecated:

Deprecated
----------

- Deprecate ``--skip-maintenance`` flag of ``pipx list``; maintenance is now never executed there (:pr:`1256`) by
  :user:`Arpafaucon`

.. _release-1-4-3:

`1.4.3 <https://github.com/pypa/pipx/tree/1.4.3>`_ - 2024-01-16
===============================================================

.. _release-1-4-3-fixed:

Fixed
-----

- Autofix python version for pylauncher, when version is provided prefixed with ``python`` (:issue:`1150`)

.. _release-1-4-3-documentation:

Documentation
-------------

- Provide useful error messages when unresolvable python version is passed (:issue:`1150`)
- Introduce towncrier for managing the changelog (:issue:`1161`)
- Add workaround for using pipx applications in shebang under macOS (:issue:`1198`)

.. _release-1-4-3-packaging:

Packaging
---------

- Support building pipx wheels with setuptools-scm<7, such as on FreeBSD. (:pr:`1208`) by :user:`henryiii`

.. _release-1-4-2:

`1.4.2 <https://github.com/pypa/pipx/tree/1.4.2>`_
==================================================

.. _release-1-4-2-added:

Added
-----

- Allow skipping maintenance tasks during list command
- Raise more user friendly error when provided ``--python`` version is not found
- Update ``pipx run`` on scripts using ``/// script`` and no ``run`` table following the updated version of PEP 723
  (:pr:`1180`) by :user:`henryiii` and :user:`dukecat0`

.. _release-1-4-2-fixed:

Fixed
-----

- Include ``tomli`` into ``pipx.pyz`` (zipapp) so that it can be executed with Python 3.10 or earlier (:issue:`1142`)
- Fix resolving the python executable path on linux
- ``pipx run``: Verify whether the script name provided is a file before running it
- Avoid repeated exception logging in a few rare cases (:pr:`1192`) by :user:`henryiii`

.. _release-1-4-1:

`1.4.1 <https://github.com/pypa/pipx/tree/1.4.1>`_
==================================================

.. _release-1-4-1-fixed:

Fixed
-----

- Set default logging level to WARNING, so debug log messages won't be shown without passing additional flags such as
  ``--verbose``

.. _release-1-4-0:

`1.4.0 <https://github.com/pypa/pipx/tree/1.4.0>`_
==================================================

.. _release-1-4-0-added:

Added
-----

- Add ``--quiet`` and ``--verbose`` options for the ``pipx`` subcommands
- Add ability to install multiple packages at once
- Delete directories directly instead of spawning rmdir on Windows

.. _release-1-4-0-fixed:

Fixed
-----

- "Failed to delete" error when using Microsoft Store Python
- "No pyvenv.cfg file" error when using Microsoft Store Python (:issue:`1164`)

.. _release-1-4-0-documentation:

Documentation
-------------

- Add Scoop installation instructions

.. _release-1-3-3:

`1.3.3 <https://github.com/pypa/pipx/tree/1.3.3>`_
==================================================

.. _release-1-3-3-documentation:

Documentation
-------------

- Make the logo more visible in dark mode

.. _release-1-3-2:

`1.3.2 <https://github.com/pypa/pipx/tree/1.3.2>`_
==================================================

.. _release-1-3-2-added:

Added
-----

- The project version number is now dynamic and generated from the VCS at build time

.. _release-1-3-2-documentation:

Documentation
-------------

- Add additional example for --pip-args option, to docs/examples.md

.. _release-1-3-1:

`1.3.1 <https://github.com/pypa/pipx/tree/1.3.1>`_
==================================================

.. _release-1-3-1-fixed:

Fixed
-----

- Fix combining of --editable and --force flag

.. _release-1-3-0:

`1.3.0 <https://github.com/pypa/pipx/tree/1.3.0>`_
==================================================

.. _release-1-3-0-added:

Added
-----

- Allow running ``pip`` with ``pipx run``
- Add ``--with-suffix`` for ``pipx inject`` command
- ``pipx install``: emit a warning when ``--force`` and ``--python`` were passed at the same time
- Add explicit 3.12 support
- Make usage message in ``pipx run`` show ``package_or_url``, so extra will be printed out as well
- Use the py launcher, if available, to select Python version with the ``--python`` option
- Add ``pipx install --preinstall`` to support preinstalling build requirements
- Return an error message when directory can't be added to PATH successfully
- Expose manual pages included in an application installed with ``pipx install``
- Check whether pip module exists in shared lib before performing any actions, such as ``reinstall-all``.
- Support `inline script metadata <https://packaging.python.org/en/latest/specifications/inline-script-metadata/>`_ in
  ``pipx run``.
- Imply ``--include-apps`` when running ``pipx inject --include-deps``
- Add ``--force-reinstall`` to pip arguments when ``--force`` was passed
- Support including requirements in scripts run using ``pipx run`` (:pr:`916`) by :user:`pfmoore`
- Pass ``pip_args`` to ``shared_libs.upgrade()``
- Fallback to user's log path if the default log path (``$PIPX_HOME/logs``) is not writable to aid with pipx being used
  for multi-user (e.g. system-wide) installs of applications
- Don't show escaped backslashes for paths in console output
- Move ``pipx`` paths to ensure compatibility with the platform-specific user directories
- Pass ``--no-input`` to pip when output is not piped to parent stdout
- Print all environment variables in ``pipx environment``
- Drop support for Python 3.7

.. _release-1-3-0-fixed:

Fixed
-----

- Fix wrong interpreter usage when injecting local pip-installable dependencies into venvs
- Fix program name in generated manual page

.. _release-1-3-0-performance:

Performance
-----------

- Drop ``setuptools`` and ``wheel`` from the shared libraries. This results in less time consumption when the libraries
  are automatically upgraded.

.. _release-1-3-0-documentation:

Documentation
-------------

- Add more examples for ``pipx run``
- Add subsection to make README easier to read

.. _release-1-2-1:

`1.2.1 <https://github.com/pypa/pipx/tree/1.2.1>`_
==================================================

.. _release-1-2-1-fixed:

Fixed
-----

- Fix compatibility to packaging 23.2+ by removing reliance on packaging's requirement validation logic and detecting a
  URL-based requirement in pipx. (:issue:`1070`)

.. _release-1-2-0:

`1.2.0 <https://github.com/pypa/pipx/tree/1.2.0>`_
==================================================

.. _release-1-2-0-added:

Added
-----

- Add ``pipx uninject`` command (:pr:`820`) by :user:`dukecat0` and :user:`cs01`
- Ship a `zipapp <https://docs.python.org/3/library/zipapp.html>`_ of pipx
- Match pip's behaviour when package name ends with archive extension (treat it as a path)
- Change the program name to ``path/to/python -m pipx`` when running as ``python -m pipx``

.. _release-1-2-0-fixed:

Fixed
-----

- Improve the detection logic for MSYS2 to avoid entering infinite loop (:pr:`908`) (:pr:`938`) by :user:`dukecat0` and
  :user:`chdka`
- Remove extra trailing quote from exception message
- Fix EncodingWarning in ``pipx_metadata_file``.

.. _release-1-2-0-documentation:

Documentation
-------------

- Add an example for installation from source with extras
- Fix ``pipx run`` examples and update Python versions used by ``pipx install`` examples

.. _release-1-1-0:

`1.1.0 <https://github.com/pypa/pipx/tree/1.1.0>`_
==================================================

.. _release-1-1-0-added:

Added
-----

- Add ``pipx environment`` command (:pr:`793`) by :user:`dukecat0` and :user:`cs01`
- Add ``list --short`` option to list only package names (:pr:`804`) by :user:`93578237`
- Improve the behaviour of ``shlex.split`` on Windows, so paths on Windows can be handled properly when they are passed
  in ``--pip-args``. (:pr:`794`) by :user:`dukecat0`
- Add additional examples for installation from git repos
- Add a CACHEDIR.TAG to the cache directory to prevent it from being included in archives and backups. For more
  information about cache directory tags, see https://bford.info/cachedir

.. _release-1-1-0-fixed:

Fixed
-----

- Fix encoding issue on Windows when pip fails to install a package

.. _release-1-1-0-documentation:

Documentation
-------------

- Add more examples
- Fix the command for `installing development version
  <https://pipx.pypa.io/stable/installation/#install-pipx-development-versions>`_. (:pr:`801`) by :user:`dukecat0`
- Fix test status badge in readme file

.. _release-1-1-0rc0:

`1.1.0rc0 <https://github.com/pypa/pipx/tree/1.1.0rc0>`_
========================================================

.. _release-1-1-0rc0-added:

Added
-----

- Add ``pipx environment`` command (:pr:`793`) by :user:`dukecat0` and :user:`cs01`
- Add ``list --short`` option to list only package names (:pr:`804`) by :user:`93578237`
- Improve the behaviour of ``shlex.split`` on Windows, so paths on Windows can be handled properly when they are passed
  in ``--pip-args``. (:pr:`794`) by :user:`dukecat0`
- Add additional examples for installation from git repos
- Add a CACHEDIR.TAG to the cache directory to prevent it from being included in archives and backups. For more
  information about cache directory tags, see https://bford.info/cachedir

.. _release-1-1-0rc0-fixed:

Fixed
-----

- Fix encoding issue on Windows when pip fails to install a package

.. _release-1-1-0rc0-documentation:

Documentation
-------------

- Add more examples
- Fix the command for `installing development version
  <https://pipx.pypa.io/stable/installation/#install-pipx-development-versions>`_. (:pr:`801`) by :user:`dukecat0`
- Fix test status badge in readme file

.. _release-1-0-0:

`1.0.0 <https://github.com/pypa/pipx/tree/1.0.0>`_
==================================================

.. _release-1-0-0-added:

Added
-----

- Support `argcomplete 2.0.0 <https://pypi.org/project/argcomplete/2.0.0>`_ (:pr:`790`) by :user:`hswong3i`
- Include machinery to build a manpage for pipx with `argparse-manpage <https://pypi.org/project/argparse-manpage/>`_.
- Add better handling for 'app not found' when a single app is present in the project, and an improved error message
  (:pr:`733`) by :user:`tusharsadhwani`

.. _release-1-0-0-fixed:

Fixed
-----

- Fixed animations sending output to stdout, which can break JSON output. (:issue:`769`)
- Fix typo in ``pipx upgrade-all`` output

.. _release-0-17-0:

`0.17.0 <https://github.com/pypa/pipx/tree/0.17.0>`_
====================================================

.. _release-0-17-0-added:

Added
-----

- Support ``pipx run`` with version constraints and extras. (:issue:`697`)

.. _release-0-16-5:

`0.16.5 <https://github.com/pypa/pipx/tree/0.16.5>`_
====================================================

.. _release-0-16-5-fixed:

Fixed
-----

- Fixed ``pipx list`` output phrasing to convey that python version displayed is the one with which package was
  installed.
- Fixed ``pipx install`` to provide return code 0 if venv already exists, similar to pip's behavior. (:pr:`736`) by
  :user:`wombelix`

.. _release-0-16-5-documentation:

Documentation
-------------

- Update ansible's install command in `Programs to Try document <https://pipx.pypa.io/stable/programs-to-try/#ansible>`_
  to work with Ansible 2.10+ (:pr:`742`) by :user:`Jackenmen`

.. _release-0-16-4:

`0.16.4 <https://github.com/pypa/pipx/tree/0.16.4>`_
====================================================

.. _release-0-16-4-fixed:

Fixed
-----

- Fix to ``pipx ensurepath`` to fix behavior in user locales other than UTF-8, to fix :issue:`644`. The internal change
  is to use userpath v1.6.0 or greater. (:pr:`700`) by :user:`itsayellow`
- Fix virtual environment inspection for Python releases that uses an int for its release serial number. (:pr:`706`) by
  :user:`uranusjr`
- Fix PermissionError in windows when pipx manages itself. (:pr:`718`) by :user:`mattmess1221`

.. _release-0-16-3:

`0.16.3 <https://github.com/pypa/pipx/tree/0.16.3>`_
====================================================

.. _release-0-16-3-changes:

Changes
-------

- Organization: pipx is extremely pleased to now be a project of the Python Packaging Authority (PyPA)! Note that our
  github URL has changed to `pypa/pipx <https://github.com/pypa/pipx>`_
- Changed ``pipx ensurepath`` bash behavior so that only one of {``~/.profile``, ``~/.bash_profile``} is modified with
  the extra pipx paths, not both. Previously, if a ``.bash_profile`` file was created where one didn't exist, it could
  cause problems, e.g. :issue:`456`. The internal change is to use userpath v1.5.0 or greater. (:pr:`684`) by
  :user:`itsayellow`

.. _release-0-16-3-fixed:

Fixed
-----

- Fixed ``pipx list --json`` to return valid json with no venvs installed. Previously would return an empty string to
  stdout. (:pr:`681`) by :user:`itsayellow`

.. _release-0-16-3-packaging:

Packaging
---------

- Colorama is now only installed on Windows. (:pr:`691`) by :user:`hwalinga`

.. _release-0-16-2-1:

`0.16.2.1 <https://github.com/pypa/pipx/tree/0.16.2.1>`_
========================================================

.. _release-0-16-2-1-changes:

Changes
-------

- Changed non-venv-info warnings and notices from ``pipx list`` to print to stderr. This especially prevents ``pipx list
  --json`` from printing invalid json to stdout. (:pr:`680`) by :user:`itsayellow`

.. _release-0-16-2-1-fixed:

Fixed
-----

- Fixed bug that could cause uninstall on Windows with injected packages to uninstall too many apps from the local
  binary directory. (:pr:`679`) by :user:`itsayellow`

.. _release-0-16-2-0:

`0.16.2.0 <https://github.com/pypa/pipx/tree/0.16.2.0>`_
========================================================

.. _release-0-16-2-0-added:

Added
-----

- Added ``--json`` switch to ``pipx list`` to output rich json-metadata for all venvs.
- Changed venv minimum python version to 3.6, removing python 3.5 which is End of Life. (:pr:`666`) by
  :user:`itsayellow`

.. _release-0-16-2-0-changes:

Changes
-------

- Ensured log files are utf-8 encoded to prevent Unicode encoding errors from occurring with emojis. (:pr:`646`) by
  :user:`itsayellow`

.. _release-0-16-2-0-fixed:

Fixed
-----

- Fixed bug :issue:`670` where uninstalling a venv could erroneously uninstall other apps from the local binary
  directory. (:pr:`672`) by :user:`itsayellow`
- Fixed issue which made pipx incorrectly list apps as part of a venv when they were not installed by pipx. (:pr:`650`)
  by :user:`itsayellow`
- Fixed old regression that would prevent pipx uninstall from cleaning up linked binaries if the venv was old and did
  not have pipx metadata. (:pr:`651`) by :user:`itsayellow`
- Fixed bugs with suffixed-venvs on Windows. Now properly summarizes install, and actually uninstalls associated
  binaries for suffixed-venvs. (:pr:`653`) by :user:`itsayellow`

.. _release-0-16-1-0:

`0.16.1.0 <https://github.com/pypa/pipx/tree/0.16.1.0>`_
========================================================

.. _release-0-16-1-0-added:

Added
-----

- Introduce the ``pipx.run`` entry point group as an alternative way to declare an application for ``pipx run``.
- Support text colors on Windows. (:pr:`612`) by :user:`itsayellow`

.. _release-0-16-1-0-changes:

Changes
-------

- Better platform unicode detection to avoid errors and allow showing emojis when possible. (:pr:`614`) by
  :user:`itsayellow`
- pip errors no longer stream to the shell when pip fails during a pipx install. pip's output is now saved to a log
  file. In the shell, pipx will tell you the location of the log file and attempt to summarize why pip failed.
  (:pr:`625`) by :user:`itsayellow`
- For ``reinstall-all``, fixed bug where missing python executable would cause error. (:pr:`634`) by :user:`itsayellow`

.. _release-0-16-1-0-fixed:

Fixed
-----

- Fix cursor show/hide to work with older versions of Windows. (:pr:`610`) by :user:`itsayellow`
- Don't emit show cursor or hide cursor codes if STDERR is not a tty. (:pr:`620`) by :user:`itsayellow`
- Fix regression which prevented pipx from working with pythonloc (and ``__pypackages__`` folder). (:pr:`636`) by
  :user:`itsayellow`

.. _release-0-16-1-0-performance:

Performance
-----------

- Sped up ``pipx list`` (:pr:`624`) by :user:`itsayellow`.

.. _release-0-16-0-0:

`0.16.0.0 <https://github.com/pypa/pipx/tree/0.16.0.0>`_
========================================================

.. _release-0-16-0-0-added:

Added
-----

- New venv inspection! The code that pipx uses to examine and determine metadata in an installed venv has been made
  faster, better, and more reliable. It now uses modern python libraries like ``packaging`` and ``importlib.metadata``
  to examine installed venvs. It also now properly handles installed package extras. In addition, some problems pipx has
  had with certain characters (like periods) in package names should be remedied.
- Added reinstall command for reinstalling a single venv.
- Venv package name arguments now do not have to match exactly as pipx has them stored, but can be specified in any
  python-package-name-equivalent way. (i.e. case does not matter, and ``.``, ``-``, ``_`` characters are
  interchangeable.)
- Autocomplete for venv names is no longer restricted to an exact match to the literal venv name, but will autocomplete
  any logically-similar python package name (i.e. case does not matter, and ``.``, ``-``, ``_`` characters are all
  equivalent.)

.. _release-0-16-0-0-changes:

Changes
-------

- Changed ``pipx run`` on non-Windows systems to actually replace pipx process with the app process instead of running
  it as a subprocess. (Now using python's ``os.exec*``)
- Venvs with a suffix: A suffix can contain any characters, but for purposes of uniqueness, python package name rules
  apply--upper- and lower-case letters are equivalent, and any number of ``.``, ``-``, or ``_`` characters in a row are
  equivalent. (e.g. if you have a suffixed venv ``pylint_1.0A`` you could not add another suffixed venv called
  ``pylint--1-0a``, as it would not be a unique name.)
- Pipx shared libraries (providing pip, setuptools, wheel to pipx) are no longer installed using pip arguments taken
  from the last regular pipx install. If you need to apply pip arguments to pipx's use of pip for its internal shared
  libraries, use ``PIP_*`` environment variables.
- pipx now reinstall its internal shared libraries when the user executes ``reinstall-all``.
- Made sure shell exit codes from every pipx command are correct. In the past some (like from ``pipx upgrade``) were
  wrong. The exit code from ``pipx runpip`` is now the exit code from the ``pip`` command run. The exit code from ``pipx
  list`` will be 1 if one or more venvs have problems that need to be addressed.
- pipx now writes a log file for each pipx command executed to ``$PIPX_HOME/logs``, typically ``~/.local/pipx/logs``.
  pipx keeps the most recent 10 logs and deletes others.
- ``pipx upgrade`` and ``pipx upgrade-all`` now have a ``--upgrade-injected`` option which directs pipx to also upgrade
  injected packages.
- ``pipx list`` now detects, identifies, and suggests a remedy for venvs with old-internal data (internal venv names)
  that need to be updated.
- pipx error, warning, and other messages now word-wrap so words are not split across lines. Their appearance is also
  now more consistent.

.. _release-0-16-0-0-fixed:

Fixed
-----

- Fixed bug with reinstall-all command when package have been installed using a specifier. Now the initial specifier is
  used.
- Override display of ``PIPX_DEFAULT_PYTHON`` value when generating web documentation for ``pipx install`` :issue:`523`
- Wrap help documentation for environment variables.
- Fixed uninstall crash that could happen on Windows for certain packages

.. _release-0-16-0-0-documentation:

Documentation
-------------

- Added a "Troubleshooting" page to the pipx web documentation for common problems pipx users may encounter.

.. _release-0-15-6-0:

`0.15.6.0 <https://github.com/pypa/pipx/tree/0.15.6.0>`_
========================================================

.. _release-0-15-6-0-added:

Added
-----

- Added support for user-defined default python interpreter via new ``PIPX_DEFAULT_PYTHON``. Helpful for use with pyenv
  among other uses.

.. _release-0-15-6-0-changes:

Changes
-------

- Updated help text to show description for ``ensurepath`` and ``completions`` help

.. _release-0-15-6-0-fixed:

Fixed
-----

- Fixed regression in list, inject, upgrade, reinstall-all commands when suffixed packages are used.
- Do not reset package url during upgrade when main package is ``pipx``
- Fixed bug where extras were ignored with a PEP 508 package specification with a URL.

.. _release-0-15-6-0-documentation:

Documentation
-------------

- Update license
- Display a more idiomatic command for registering completions on fish.

.. _release-0-15-5-1:

`0.15.5.1 <https://github.com/pypa/pipx/tree/0.15.5.1>`_
========================================================

.. _release-0-15-5-1-fixed:

Fixed
-----

- Fixed regression of 0.15.5.0 which erroneously made installing from a local path with package extras not possible.

.. _release-0-15-5-0:

`0.15.5.0 <https://github.com/pypa/pipx/tree/0.15.5.0>`_
========================================================

.. _release-0-15-5-0-added:

Added
-----

- Version of each injected package is now listed after name for ``pipx list --include-injected``
- ``ensurepath`` now also ensures that pip user binary path containing pipx itself is in user's PATH if pipx was
  installed using ``pip install --user``.
- log pipx version (:issue:`423`)
- ``--suffix`` option for ``install`` to allow multiple versions of same tool to be installed (:pr:`445`) by
  :user:`joshbode`
- pipx can now be used with the Windows embeddable Python distribution

.. _release-0-15-5-0-changes:

Changes
-------

- pipx now parses package specification before install. It removes (with warning) the ``--editable`` install option for
  any package specification that is not a local path. It also removes (with warning) any environment markers.
- Disabled animation when we cannot determine terminal size or if the number of columns is too small. (Fixes
  :issue:`444`)
- Change metadata recorded from version-specified install to allow upgrades in future. Adds pipx dependency on
  ``packaging`` package.

.. _release-0-15-5-0-fixed:

Fixed
-----

- Prevent python error in case where package has no pipx metadata and advise user how to fix.
- For ``pipx install``, fixed failure to install if user has ``PIP_USER=1`` or ``user=true`` in pip.conf. (:issue:`110`)
- Requiring userpath v1.4.1 or later so ensure Windows bug is fixed for ``ensurepath`` (:issue:`437`)

.. _release-0-15-4-0:

`0.15.4.0 <https://github.com/pypa/pipx/tree/0.15.4.0>`_
========================================================

.. _release-0-15-4-0-added:

Added
-----

- ``list`` now has a new option ``--include-injected`` to show the injected packages in the main apps

.. _release-0-15-4-0-fixed:

Fixed
-----

- Fixed bug that can cause crash when installing an app

.. _release-0-15-3-1:

`0.15.3.1 <https://github.com/pypa/pipx/tree/0.15.3.1>`_
========================================================

.. _release-0-15-3-1-fixed:

Fixed
-----

- Workaround multiprocessing issues on certain platforms (:issue:`229`)

.. _release-0-15-3-0:

`0.15.3.0 <https://github.com/pypa/pipx/tree/0.15.3.0>`_
========================================================

.. _release-0-15-3-0-added:

Added
-----

- Use symlinks on Windows when symlinks are available

.. _release-0-15-2-0:

`0.15.2.0 <https://github.com/pypa/pipx/tree/0.15.2.0>`_
========================================================

.. _release-0-15-2-0-added:

Added
-----

- Add environment variable ``USE_EMOJI`` to allow enabling/disabling emojis (:issue:`376`)

.. _release-0-15-2-0-fixed:

Fixed
-----

- Improved error reporting during venv metadata inspection.
- Fixed incompatibility with pypy as venv interpreter (:issue:`372`).
- Replaced implicit dependency on setuptools with an explicit dependency on packaging (:issue:`339`).
- Continue reinstalling packages after failure
- Hide cursor while pipx runs
- Ignore system shared libraries when installing shared libraries pip, wheel, and setuptools. This also fixes an
  incompatibility with Debian/Ubuntu's version of pip (:issue:`386`).

.. _release-0-15-1-3:

`0.15.1.3 <https://github.com/pypa/pipx/tree/0.15.1.3>`_
========================================================

.. _release-0-15-1-3-fixed:

Fixed
-----

- On Windows, pipx now lists correct Windows apps (:issue:`217`)
- Fixed a ``pipx install`` bug causing incorrect python binary to be used when using the optional --python argument in
  certain situations, such as running pipx from a Framework python on macOS and specifying a non-Framework python.

.. _release-0-15-1-2:

`0.15.1.2 <https://github.com/pypa/pipx/tree/0.15.1.2>`_
========================================================

.. _release-0-15-1-2-changes:

Changes
-------

- ``upgrade-all`` now skips editable packages, because pip disallows upgrading editable packages.

.. _release-0-15-1-2-fixed:

Fixed
-----

- Fix recursive search of dependencies' apps so no apps are missed.

.. _release-0-15-1-1:

`0.15.1.1 <https://github.com/pypa/pipx/tree/0.15.1.1>`_
========================================================

.. _release-0-15-1-1-fixed:

Fixed
-----

- fix regression that caused installing with --editable flag to fail package name determination.

.. _release-0-15-1-0:

`0.15.1.0 <https://github.com/pypa/pipx/tree/0.15.1.0>`_
========================================================

.. _release-0-15-1-0-added:

Added
-----

- Add Python 3.8 to PyPI classifier and travis test matrix
- auto-upgrade shared libraries, including pip, if older than one month. Hide all pip warnings that a new version is
  available. (:issue:`264`)

.. _release-0-15-1-0-fixed:

Fixed
-----

- pass pip arguments to pip when determining package name (:issue:`320`)

.. _release-0-15-0-0:

`0.15.0.0 <https://github.com/pypa/pipx/tree/0.15.0.0>`_
========================================================

.. _release-0-15-0-0-added:

Added
-----

- Add printed summary after successful call to ``pipx inject``
- Support associating apps with Python 3.5

.. _release-0-15-0-0-changes:

Changes
-------

- Upgrade instructions: When upgrading to 0.15.0.0 or above from a pre-0.15.0.0 version, you must re-install all
  packages to take advantage of the new persistent pipx metadata files introduced in this release. These metadata files
  store pip specification values, injected packages, any custom pip arguments, and more in each main package's venv. You
  can do this by running ``pipx reinstall-all`` or ``pipx uninstall-all``, then reinstalling manually.
- ``inject`` will now accept pip specifications for dependency arguments
- Metadata is now stored for each application installed, including install options like ``--spec``, and injected
  packages. This information allows upgrade, upgrade-all and reinstall-all to work properly even with non-pypi installed
  packages. (:pr:`222`) by :user:`itsayellow`
- Handle missing interpreters more gracefully (:issue:`146`)
- Change ``reinstall-all`` to use system python by default for apps. Now use ``--python`` option to specify a different
  python version.
- Remove the PYTHONPATH environment variable when executing any command to prevent conflicts between pipx dependencies
  and package dependencies when pipx is installed via homebrew. Homebrew can use PYTHONPATH manipulation instead of
  virtual environments. (:issue:`233`)
- Improvements to animation status text
- Make ``--python`` argument in ``reinstall-all`` command optional
- Stricter parsing when passing ``--`` argument as delimiter

.. _release-0-15-0-0-removed:

Removed
-------

- ``install`` now has no ``--spec`` option. You may specify any valid pip specification for ``install``'s main argument.
- ``upgrade`` options ``--spec`` and ``--include-deps`` were removed. Pipx now uses the original options used to install
  each application instead. (:pr:`222`) by :user:`itsayellow`
- ``upgrade-all`` options ``--include-deps``, ``--system-site-packages``, ``--index-url``, ``--editable``, and
  ``--pip-args`` were removed. Pipx now uses the original options used to install each application instead. (:pr:`222`)
  by :user:`itsayellow`
- ``reinstall-all`` options ``--include-deps``, ``--system-site-packages``, ``--index-url``, ``--editable``, and
  ``--pip-args`` were removed. Pipx now uses the original options used to install each application instead. (:pr:`222`)
  by :user:`itsayellow`

.. _release-0-14-0-0:

`0.14.0.0 <https://github.com/pypa/pipx/tree/0.14.0.0>`_
========================================================

.. _release-0-14-0-0-changes:

Changes
-------

- Change all terminology from ``binary`` to ``app`` or ``application``
- Improve argument parsing for ``pipx run`` and ``pipx runpip``
- If ``--force`` is passed, remove existing files in PIPX_BIN_DIR
- Move animation to start of line, hide cursor when animating

.. _release-0-14-0-0-performance:

Performance
-----------

- Speed up operations by using shared venv for ``pip``, ``setuptools``, and ``wheel``. You can see more detail in the
  'how pipx works' section of the documentation. (:issue:`164`) by :user:`pfmoore`.

.. _release-0-14-0-0-breaking-changes:

Breaking changes
----------------

- Breaking change: for the ``inject`` command, change ``--include-binaries`` to ``--include-apps``

.. _release-0-14-0-0rc1:

`0.14.0.0rc1 <https://github.com/pypa/pipx/tree/0.14.0.0rc1>`_
==============================================================

.. _release-0-14-0-0rc1-changes:

Changes
-------

- Change all terminology from ``binary`` to ``app`` or ``application``
- Improve argument parsing for ``pipx run`` and ``pipx runpip``
- If ``--force`` is passed, remove existing files in PIPX_BIN_DIR
- Move animation to start of line, hide cursor when animating

.. _release-0-14-0-0rc1-performance:

Performance
-----------

- Speed up operations by using shared venv for ``pip``, ``setuptools``, and ``wheel``. You can see more detail in the
  'how pipx works' section of the documentation. (:issue:`164`) by :user:`pfmoore`.

.. _release-0-14-0-0rc1-breaking-changes:

Breaking changes
----------------

- Breaking change: for the ``inject`` command, change ``--include-binaries`` to ``--include-apps``

.. _release-0-13-2-3:

`0.13.2.3 <https://github.com/pypa/pipx/tree/0.13.2.3>`_
========================================================

.. _release-0-13-2-3-fixed:

Fixed
-----

- Fix regression when installing a package that doesn't have any entry points

.. _release-0-13-2-2:

`0.13.2.2 <https://github.com/pypa/pipx/tree/0.13.2.2>`_
========================================================

.. _release-0-13-2-2-changes:

Changes
-------

- Make status text/animation reliably disappear before continuing
- Update animation symbols

.. _release-0-13-2-2-fixed:

Fixed
-----

- Remove unnecessary and sometimes incorrect check after ``pipx inject`` (:issue:`195`)

.. _release-0-13-2-1:

`0.13.2.1 <https://github.com/pypa/pipx/tree/0.13.2.1>`_
========================================================

.. _release-0-13-2-1-fixed:

Fixed
-----

- Remove virtual environment if installation did not complete. For example, if it was interrupted by ctrl+c or if an
  exception occurred for any reason. (:issue:`193`)

.. _release-0-13-2-0:

`0.13.2.0 <https://github.com/pypa/pipx/tree/0.13.2.0>`_
========================================================

.. _release-0-13-2-0-added:

Added
-----

- Add shell autocompletion. Also add ``pipx completions`` command to print instructions on how to add pipx completions
  to your shell.
- Un-deprecate ``ensurepath``. Use ``userpath`` internally instead of instructing users to run the ``userpath`` cli
  command.

.. _release-0-13-2-0-changes:

Changes
-------

- Improve error message when an existing symlink exists in PIPX_BIN_DIR and points to the wrong location

.. _release-0-13-2-0-fixed:

Fixed
-----

- Improve detection of PIPX_BIN_DIR not being on PATH
- Improve handling of unexpected files in PIPX_HOME by :user:`uranusjr`.
- Swap out-of-order logic to recommend ``--include-deps`` correctly by :user:`joshuarli`.

.. _release-0-13-1-1:

`0.13.1.1 <https://github.com/pypa/pipx/tree/0.13.1.1>`_
========================================================

.. _release-0-13-1-1-changes:

Changes
-------

- Update pipsi migration script

.. _release-0-13-1-1-fixed:

Fixed
-----

- Do not raise bare exception if no binaries found (:pr:`150`) by :user:`cs01`

.. _release-0-13-1-0:

`0.13.1.0 <https://github.com/pypa/pipx/tree/0.13.1.0>`_
========================================================

.. _release-0-13-1-0-added:

Added
-----

- Support redirects and proxies when downloading python files (i.e. ``pipx run http://url/file.py``)

.. _release-0-13-1-0-changes:

Changes
-------

- Change default cache duration for ``pipx run`` from 2 to 14 days

.. _release-0-13-1-0-deprecated:

Deprecated
----------

- Deprecate ``ensurepath`` command. Use ``userpath append ~/.local/bin``

.. _release-0-13-0-1:

`0.13.0.1 <https://github.com/pypa/pipx/tree/0.13.0.1>`_
========================================================

.. _release-0-13-0-1-fixed:

Fixed
-----

- Fix upgrade-all and reinstall-all regression

.. _release-0-13-0-0:

`0.13.0.0 <https://github.com/pypa/pipx/tree/0.13.0.0>`_
========================================================

.. _release-0-13-0-0-added:

Added
-----

- Add ``runpip`` command to run arbitrary pip commands in pipx-managed virtual environments
- Add ``--skip`` argument to ``upgrade-all`` and ``reinstall-all`` commands, to let the user skip particular packages

.. _release-0-13-0-0-fixed:

Fixed
-----

- Do not raise error when running ``pipx install PACKAGE`` and the package has already been installed by pipx
  (:issue:`125`). This is the cause of the major version change from 0.12 to 0.13.

.. _release-0-12-3-3:

`0.12.3.3 <https://github.com/pypa/pipx/tree/0.12.3.3>`_
========================================================

.. _release-0-12-3-3-fixed:

Fixed
-----

- Update logic in determining a package's binaries during installation. This removes spurious binaries from the
  installation. (:issue:`104`)
- Improve compatibility with Debian distributions by using ``shutil.which`` instead of
  ``distutils.spawn.find_executable`` (:issue:`102`)

.. _release-0-12-3-2:

`0.12.3.2 <https://github.com/pypa/pipx/tree/0.12.3.2>`_
========================================================

.. _release-0-12-3-2-fixed:

Fixed
-----

- Fix infinite recursion error when installing package such as ``cloudtoken==0.1.84`` (:issue:`103`)
- Fix windows type errors (:issue:`96`, :issue:`98`)

.. _release-0-12-3-1:

`0.12.3.1 <https://github.com/pypa/pipx/tree/0.12.3.1>`_
========================================================

.. _release-0-12-3-1-fixed:

Fixed
-----

- Fix "WindowsPath is not iterable" bug

.. _release-0-12-3-0:

`0.12.3.0 <https://github.com/pypa/pipx/tree/0.12.3.0>`_
========================================================

.. _release-0-12-3-0-added:

Added
-----

- Add ``--include-deps`` argument to include binaries of dependent packages when installing with pipx. This improves
  compatibility with packages that depend on other installed packages, such as ``jupyter``.

.. _release-0-12-3-0-changes:

Changes
-------

- More aggressive cache directory removal when ``--no-cache`` is passed to ``pipx run``

.. _release-0-12-3-0-performance:

Performance
-----------

- Speed up ``pipx list`` output (by running multiple processes in parallel) and by collecting all metadata in a single
  subprocess call

.. _release-0-12-2-0:

`0.12.2.0 <https://github.com/pypa/pipx/tree/0.12.2.0>`_
========================================================

.. _release-0-12-2-0-added:

Added
-----

- Add support for PEP 582's ``__pypackages__`` (experimental). ``pipx run BINARY`` will first search in
  ``__pypackages__`` for binary, then fallback to installing from PyPI. ``pipx run --pypackages BINARY`` will raise an
  error if the binary is not found in ``__pypackages__``.

.. _release-0-12-2-0-fixed:

Fixed
-----

- Fix regression when installing with ``--editable`` flag (:issue:`93`)

.. _release-0-12-1-0:

`0.12.1.0 <https://github.com/pypa/pipx/tree/0.12.1.0>`_
========================================================

.. _release-0-12-1-0-added:

Added
-----

- Cache and reuse temporary Virtual Environments created with ``pipx run`` (:issue:`61`)

.. _release-0-12-1-0-changes:

Changes
-------

- When using environment variable PIPX_HOME, Virtual Environments will now be created at ``$PIPX_HOME/venvs`` rather
  than at ``$PIPX_HOME``.

.. _release-0-12-1-0-fixed:

Fixed
-----

- Update binary discovery logic to find "scripts" like awscli (:issue:`91`)
- Forward ``--pip-args`` to the pip upgrade command (previously the args were forwarded to install/upgrade commands for
  packages) (:issue:`77`)

.. _release-0-12-0-4:

`0.12.0.4 <https://github.com/pypa/pipx/tree/0.12.0.4>`_
========================================================

.. _release-0-12-0-4-fixed:

Fixed
-----

- Fix parsing bug in pipx run

.. _release-0-12-0-3:

`0.12.0.3 <https://github.com/pypa/pipx/tree/0.12.0.3>`_
========================================================

.. _release-0-12-0-3-added:

Added
-----

- list python2 as supported language so that pip installs with python2 will no longer install the pipx on PyPI from the
  original pipx owner. Running pipx with python2 will fail, but at least it will not be as confusing as running the pipx
  package from the original owner.

.. _release-0-12-0-2:

`0.12.0.2 <https://github.com/pypa/pipx/tree/0.12.0.2>`_
========================================================

.. _release-0-12-0-2-changes:

Changes
-------

- forward arguments to run command correctly :issue:`90`

.. _release-0-12-0-1:

`0.12.0.1 <https://github.com/pypa/pipx/tree/0.12.0.1>`_
========================================================

.. _release-0-12-0-1-fixed:

Fixed
-----

- stop using unverified context :issue:`89`

.. _release-0-12-0-0:

`0.12.0.0 <https://github.com/pypa/pipx/tree/0.12.0.0>`_
========================================================

.. _release-0-12-0-0-added:

Added
-----

- Add ``ensurepath`` command

.. _release-0-12-0-0-documentation:

Documentation
-------------

- Change installation instructions to use ``pipx`` PyPI name

.. _release-0-11-0-2:

`0.11.0.2 <https://github.com/pypa/pipx/tree/0.11.0.2>`_
========================================================

.. _release-0-11-0-2-fixed:

Fixed
-----

- add version argument parsing back in (fixes regression)

.. _release-0-11-0-1:

`0.11.0.1 <https://github.com/pypa/pipx/tree/0.11.0.1>`_
========================================================

.. _release-0-11-0-1-documentation:

Documentation
-------------

- Update installation instructions.

.. _release-0-11-0-1-added:

Added
-----

- Add version and command checks.

.. _release-0-11-0-1-fixed:

Fixed
-----

- Fix the printed version.

.. _release-0-11-0-0:

`0.11.0.0 <https://github.com/pypa/pipx/tree/0.11.0.0>`_
========================================================

.. _release-0-11-0-0-added:

Added
-----

- support --system-site-packages flag (Issue :issue:`64`)

.. _release-0-11-0-0-changes:

Changes
-------

- upgrade pip when upgrading packages (Issue :issue:`72`)

.. _release-0-11-0-0-breaking-changes:

Breaking changes
----------------

- Replace ``pipx BINARY`` with ``pipx run BINARY`` to run a binary in an ephemeral environment. This is a breaking API
  change so the major version has been incremented. (Issue :issue:`69`)

.. _release-0-10-4-1:

`0.10.4.1 <https://github.com/pypa/pipx/tree/0.10.4.1>`_
========================================================

.. _release-0-10-4-1-fixed:

Fixed
-----

- Fix version printed when ``pipx --version`` is run

.. _release-0-10-4-0:

`0.10.4.0 <https://github.com/pypa/pipx/tree/0.10.4.0>`_
========================================================

.. _release-0-10-4-0-added:

Added
-----

- Add --index-url, --editable, and --pip-args flags

.. _release-0-10-4-0-documentation:

Documentation
-------------

- Updated README with pipsi migration instructions

.. _release-0-10-3-0:

`0.10.3.0 <https://github.com/pypa/pipx/tree/0.10.3.0>`_
========================================================

.. _release-0-10-3-0-added:

Added
-----

- Display python version in list

.. _release-0-10-3-0-changes:

Changes
-------

- Do not reinstall package if already installed (added ``--force`` flag to override)
- When upgrading all packages, print message only when package is updated

.. _release-0-10-3-0-fixed:

Fixed
-----

- Avoid accidental execution of ``pipx.__main__``
