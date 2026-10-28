#######################
 Environment variables
#######################

pipx has no user configuration file. Every setting is an environment variable, all of them optional. Run ``pipx
environment`` to print each variable as set in your environment, followed by the values pipx derives from them.

*******************
 Settable variables
*******************

.. list-table::
    :header-rows: 1
    :widths: 34 66

    - - Variable
      - Meaning and default
    - - ``PIPX_HOME``
      - Root directory for pipx virtual environments. Default: ``platformdirs.user_data_path("pipx")`` — Linux
        ``~/.local/share/pipx``, macOS ``~/Library/Application Support/pipx``, Windows ``%LOCALAPPDATA%\pipx\pipx``.
    - - ``PIPX_BIN_DIR``
      - Directory for application entry-point symlinks. Default: ``~/.local/bin``.
    - - ``PIPX_MAN_DIR``
      - Directory for man page symlinks. Default: ``~/.local/share/man``.
    - - ``PIPX_COMPLETION_DIR``
      - Directory for shell completion symlinks. Default: ``~/.local/share``.
    - - ``PIPX_GLOBAL_HOME``
      - Root directory for global (``--global``) virtual environments. Default: ``/opt/pipx``.
    - - ``PIPX_GLOBAL_BIN_DIR``
      - Entry-point directory for global installs. Default: ``/usr/local/bin``.
    - - ``PIPX_GLOBAL_MAN_DIR``
      - Man page directory for global installs. Default: ``/usr/local/share/man``.
    - - ``PIPX_GLOBAL_COMPLETION_DIR``
      - Shell completion directory for global installs. Default: ``/usr/local/share``.
    - - ``PIPX_SHARED_LIBS``
      - Override the shared libraries directory. Ignored with ``--global``. Default: ``$PIPX_HOME/shared``.
    - - ``PIPX_DEFAULT_PYTHON``
      - Python interpreter used when ``--python`` is not passed: a path, or a command name (``python3.12``) or version
        (``3.12``) looked up on ``PATH``. Default: the interpreter running pipx (``sys.executable``); on Windows,
        unless pipx runs inside a venv, the ``py`` launcher's default Python or ``python`` on ``PATH``.
    - - ``PIPX_DEFAULT_BACKEND``
      - Backend for new venvs, ``pip`` or ``uv``. Default: ``uv`` when uv 0.9.17 or newer is available, else ``pip``.
    - - ``PIPX_COOLDOWN``
      - Default for ``--cooldown``: ignore index artifacts uploaded fewer than this many days ago, on ``install``,
        ``install-all``, ``inject``, ``upgrade``, ``upgrade-all`` and ``run``. An explicit ``--cooldown`` wins, and
        ``--cooldown 0`` opts a single command out. A locked install ignores it. Default: unset.
    - - ``PIPX_FETCH_PYTHON``
      - When to fetch a standalone Python build: ``always``, ``missing``, or ``never``. Default: ``never``.
    - - ``PIPX_FETCH_MISSING_PYTHON``
      - Deprecated alias for ``PIPX_FETCH_PYTHON=missing``. Default: unset.
    - - ``PIPX_DISABLE_SHARED_LIBS_AUTO_UPGRADE``
      - Set to a truthy value to skip automatic shared library upgrades. Default: unset.
    - - ``PIPX_USE_EMOJI``
      - Set to ``1``, ``y``, ``yes``, ``t``, ``true``, or ``on`` (case-insensitive) to force emoji output; any other
        value disables it. Default: enabled when the stderr encoding supports the emoji glyphs.
    - - ``PIPX_MAX_LOGS``
      - Number of command logs to keep in the log directory, counting the current command's; pip and uv error logs
        share a separate limit of the same size. ``0`` acts like ``1``. Logs of commands still running are kept.
        Default: ``10``.

.. note::

    ``USE_EMOJI`` (unprefixed) is honored as a fallback when ``PIPX_USE_EMOJI`` is unset.

.. note::

    pipx forwards the standard ``PIP_*`` environment variables (for example ``PIP_INDEX_URL``) to pip, except that it
    forces ``PIP_USER=0`` and ``PIP_DISABLE_PIP_VERSION_CHECK=1``, drops ``PIP_TARGET``, and defaults
    ``PIP_KEYRING_PROVIDER`` to ``subprocess``. See :doc:`Troubleshoot <../how-to/troubleshoot>` if pip behaves
    unexpectedly.

Legacy fallback home
====================

If a legacy home directory already exists on disk, pipx keeps its virtual environments there instead of the
``PIPX_HOME`` default: ``~/.local/pipx`` on any platform, and ``~\pipx`` on Windows. These are used only when present
and when ``PIPX_HOME`` is unset. See :doc:`Configure paths <../how-to/configure-paths>` to migrate off them.

On Unix, a pipx installation that manages itself recovers ``PIPX_HOME`` and ``PIPX_DEFAULT_PYTHON`` from its own
virtual environment when those variables are unset, and ``PIPX_BIN_DIR`` when pipx was launched through its exposed
link, so later shells stay attached to the same installation. A pipx installed with ``--global`` lives in the global
home (``PIPX_GLOBAL_HOME``, ``/opt/pipx`` by default) and recovers only ``PIPX_DEFAULT_PYTHON``: without ``--global``
it uses the per-user defaults, with ``--global`` the global ones. A custom ``PIPX_GLOBAL_HOME`` must be set for every
user who runs that pipx; otherwise it treats the global home as their own ``PIPX_HOME``. ``PIPX_DEFAULT_PYTHON`` is
recovered only while the recorded interpreter still resolves to the one pipx's environment runs on; a record left
pointing into a removed bootstrap environment is ignored, and pipx falls back to its own interpreter.

*******************************
 Derived (read-only) values
*******************************

``pipx environment`` also reports the following values. pipx computes them from the settable variables and the
platform; they are reported, not set.

.. list-table::
    :header-rows: 1
    :widths: 40 60

    - - Value
      - Meaning
    - - ``PIPX_LOCAL_VENVS``
      - Directory holding the per-package virtual environments (``$PIPX_HOME/venvs``).
    - - ``PIPX_LOG_DIR``
      - Directory holding command logs.
    - - ``PIPX_TRASH_DIR``
      - Staging directory for deletions on the same filesystem as the venvs.
    - - ``PIPX_VENV_CACHEDIR``
      - Cache directory for ``pipx run`` environments.
    - - ``PIPX_STANDALONE_PYTHON_CACHEDIR``
      - Cache directory for downloaded standalone Python builds.
    - - ``PIPX_RESOLVED_BACKEND``
      - Backend pipx resolved for new venvs (``pip`` or ``uv``).
    - - ``PIPX_BACKEND_SOURCE``
      - Where the resolved backend came from: ``env``, ``auto-bundled``, ``auto-path``, or ``auto-pip``.
    - - ``PIPX_UV_BINARY``
      - Path to the uv binary pipx would use, or empty when none is found.
    - - ``UV_CACHE_DIR``
      - Value of ``UV_CACHE_DIR`` in the environment, passed through to uv.
