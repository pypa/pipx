from __future__ import annotations

__lazy_modules__ = [
    "datetime",
    "hashlib",
    "hmac",
    "json",
    "packaging.requirements",
    "packaging.utils",
    "pathlib",
    "pipx",
    "pipx.backends",
    "pipx.commands.common",
    "pipx.commands.run_uv",
    "pipx.options",
    "pipx.package_specifier",
    "pipx.requires_python",
    "pipx.script",
    "pipx.util",
    "pipx.venv",
    "pipx.wrap",
    "secrets",
    "shutil",
    "tempfile",
    "urllib.parse",
]

import datetime as dt
import hashlib
import hmac
import json
import logging
import os
import secrets
import sys
import tempfile
import urllib.parse
from contextlib import contextmanager
from pathlib import Path
from shutil import which
from typing import TYPE_CHECKING, Final, NoReturn

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from pipx import paths
from pipx.backends import UV, resolve_backend_name
from pipx.commands.common import package_name_from_spec
from pipx.commands.run_uv import run_script_via_uv_run, run_via_uv_tool_run
from pipx.constants import TEMP_VENV_EXPIRATION_THRESHOLD_DAYS, WINDOWS, FetchPythonOptions
from pipx.emojis import HAZARD
from pipx.options import ExposureOptions
from pipx.package_specifier import absolute_path_pip_args, resolve_local_path
from pipx.requires_python import interpreter_for, unsatisfied_by_interpreter
from pipx.script import ScriptMetadata, download_script, local_script, read_script_metadata
from pipx.util import PipxError, exec_app, get_pypackage_bin_path, redact_url_credentials, rmdir, run_pypackage_bin
from pipx.venv import Venv, VenvContainer
from pipx.wrap import pipx_wrap

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    from pipx.options import BackendOptions, CooldownOptions

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

_VENV_EXPIRED_FILENAME: Final[str] = "pipx_expired_venv"
_RUN_KEY_FILENAME: Final[str] = ".run-key"
_RUN_KEY_BYTES: Final[int] = 32


def run(  # ruff:ignore[too-many-arguments]  # mirrors the flat `pipx run` CLI options across the script/uvx/venv paths
    *,
    app: str,
    spec: str | None,
    dependencies: list[str],
    app_args: list[str],
    python: str,
    pip_args: list[str],
    venv_args: list[str],
    is_path: bool,
    pypackages: bool,
    verbose: bool,
    use_cache: bool,
    python_args: list[str],
    refresh: bool,
    no_path_check: bool,
    backend: BackendOptions,
    cooldown: CooldownOptions,
    python_flag_passed: bool,
    fetch_python: FetchPythonOptions,
) -> NoReturn:
    requirement_name: Final[str] = _requirement_name(app)
    package_name: Final[str] = canonicalize_name(requirement_name) if spec is None else requirement_name
    # a VCS URL names no script at all, and a normalized name is no longer the one on disk (`pip_search` installs a
    # `pip_search` script but canonicalizes to `pip-search`), so pipx picks the app from the installed entry points
    infer_app_name: Final[bool] = spec is None and (_is_vcs_url(app) or package_name != requirement_name)

    # the resolved backend only picks the route, uv tool run or a venv; the venv still gets the CLI and environment
    # values apart, so it attributes the backend to the right source
    resolved_backend, _ = resolve_backend_name(cli_value=backend.cli, env_value=backend.env)
    # uv cannot discover inferred app names or pipx.run entry points before installing the package
    use_uvx: Final[bool] = (
        resolved_backend == UV
        and not pypackages
        and not python_args
        and not infer_app_name
        and _can_use_uvx_for_spec(app, spec)
    )

    if spec is None and (content := maybe_script_content(app, is_path=is_path)) is not None:
        _run_script(
            content,
            app_args,
            python,
            pip_args,
            venv_args,
            verbose=verbose,
            use_cache=use_cache,
            refresh=refresh,
            backend=backend,
            resolved_backend=resolved_backend,
            script_source=Path(app) if isinstance(content, Path) else None,
            dependencies=dependencies,
            cooldown_days=cooldown.days,
            python_args=python_args,
            python_flag_passed=python_flag_passed,
            fetch_python=fetch_python,
        )
    elif use_uvx:
        run_via_uv_tool_run(
            app=package_name if spec is None else app,
            package_or_url=spec if spec is not None else app,
            dependencies=dependencies,
            app_args=app_args,
            python=python,
            pip_args=pip_args,
            venv_args=venv_args,
            use_cache=use_cache,
            refresh=refresh,
            verbose=verbose,
            no_path_check=no_path_check,
            cooldown_days=cooldown.days,
        )
    else:
        run_package(
            package_name,
            spec if spec is not None else app,
            dependencies,
            app_args,
            python,
            pip_args=pip_args,
            venv_args=venv_args,
            pypackages=pypackages,
            verbose=verbose,
            use_cache=use_cache,
            refresh=refresh,
            infer_app_name=infer_app_name,
            backend=backend,
            resolved_backend=resolved_backend,
            no_path_check=no_path_check,
            cooldown_days=cooldown.days,
            python_args=python_args,
        )


def _requirement_name(app: str) -> str:
    try:
        return Requirement(app).name
    except InvalidRequirement:
        return app


def _is_vcs_url(value: str) -> bool:
    vcs, separator, _ = urllib.parse.urlparse(value).scheme.partition("+")
    return bool(separator) and vcs in {"bzr", "git", "hg", "svn"}


def _can_use_uvx_for_spec(app: str, spec: str | None) -> bool:
    if spec is None:
        return True
    try:
        return app == canonicalize_name(Requirement(spec).name)
    except InvalidRequirement:
        return False


def maybe_script_content(app: str, *, is_path: bool) -> str | Path | None:
    app_path: Final[Path] = Path(app)
    if app_path.is_file():
        return app_path
    # a named pipe yields its content once, so read it here for both the metadata check and the interpreter
    if app_path.is_fifo():
        return app_path.read_text(encoding="utf-8")

    if is_path:
        msg = f"The specified path {app} does not exist"
        raise PipxError(msg)

    if (parsed := urllib.parse.urlparse(app)).scheme:
        if _is_vcs_url(app):
            return None
        # match on the URL path so a query string such as ``script.py?raw=1`` is still recognised
        if not parsed.path.lower().endswith(".py"):
            msg = """
                pipx will only execute apps from the internet directly if they
                end with '.py'. To run a package from another URL, use
                'pipx run --spec URL BINARY'.
                """
            raise PipxError(msg)
        _LOGGER.info("Detected url. Downloading and executing as a Python file.")

        return download_script(app)

    return None


def _run_script(  # ruff:ignore[too-many-arguments]  # mirrors the flat `pipx run` script options; a struct would only relocate them
    content: str | Path,
    app_args: list[str],
    python: str,
    pip_args: list[str],
    venv_args: list[str],
    *,
    verbose: bool,
    use_cache: bool,
    python_args: list[str],
    refresh: bool,
    backend: BackendOptions,
    resolved_backend: str,
    script_source: Path | None,
    dependencies: list[str],
    cooldown_days: int | None,
    python_flag_passed: bool,
    fetch_python: FetchPythonOptions,
) -> NoReturn:
    try:
        metadata: Final[ScriptMetadata | None] = read_script_metadata(content)
    except ValueError as error:
        msg = f"Invalid inline script metadata: {error}"
        raise PipxError(msg) from error
    requirements = None if metadata is None else list(metadata.dependencies)

    if dependencies:
        if requirements is None:
            # a plain script has no requirements list for ``--with`` to extend
            msg = (
                "--with packages can only be applied to scripts with PEP 723 inline metadata "
                "(`# /// script` block). Add the dependencies to the script's metadata or run "
                "via `pipx run --spec`."
            )
            raise PipxError(msg)
        requirements = [*requirements, *dependencies]

    # uv treats the --python pipx hands it as an explicit request and runs a script on it even when requires-python
    # rules it out, so pipx settles the interpreter for both backends
    if metadata is not None and metadata.requires_python is not None:
        python = _interpreter_for_script(
            metadata.requires_python, python, fetch_python, python_flag_passed=python_flag_passed
        )

    if resolved_backend == UV and requirements is not None and not python_args:
        if script_source is not None:
            # uv keys its own script environment on the path alone and reuses it while it satisfies the script, so a
            # changed index or cooldown, or --refresh, would keep running what an earlier request installed
            venv_dir = _get_temporary_venv_path(
                ["--script", str(script_source.resolve())],
                python,
                pip_args,
                venv_args,
                UV,
                cooldown_days=cooldown_days,
            )
            with _locked_venv_cache(venv_dir):
                _prepare_venv_cache(Venv(venv_dir, backend=backend), None, use_cache=use_cache, refresh=refresh)
            # on Windows exec_app waits for the script, so holding the lock across it would block every concurrent run
            # of this script, including one the script starts itself; uv locks the environment while it syncs
            run_script_via_uv_run(
                script_path=script_source,
                venv_dir=venv_dir,
                app_args=app_args,
                python=python,
                pip_args=pip_args,
                venv_args=venv_args,
                use_cache=use_cache,
                verbose=verbose,
                refresh=refresh,
                dependencies=dependencies,
                cooldown_days=cooldown_days,
            )
        # URL and named-pipe content has no path on disk to hand to ``uv run --script``
        _LOGGER.warning(
            pipx_wrap(
                f"""
                {HAZARD}  Script content is not a local file; building a
                pipx-managed venv via the uv backend instead of `uv run
                --script`. The uv cache and uv-managed Python features
                will not apply to this run.
                """,
                subsequent_indent=" " * 4,
            )
        )

    if not requirements:
        _exec_script(Path(python), content, app_args, python_args)

    # keyed on the requirements rather than the script name, so scripts that need the same packages share one
    # environment; read_script_metadata normalizes them so spacing differences do not split the cache
    pip_args = absolute_path_pip_args(pip_args, Path.cwd())
    venv_dir = _get_temporary_venv_path(
        requirements,
        python,
        pip_args,
        venv_args,
        resolved_backend,
        cooldown_days=cooldown_days,
    )
    with _locked_venv_cache(venv_dir):
        venv = Venv(venv_dir, backend=backend)
        _prepare_venv_cache(venv, None, use_cache=use_cache, refresh=refresh)
        if venv_dir.exists():
            _LOGGER.info("Reusing cached venv %s", venv_dir)
        else:
            venv = Venv(venv_dir, python=python, verbose=verbose, backend=backend)
            venv.check_upgrade_shared_libs(pip_args=pip_args, verbose=verbose)
            try:
                venv.create_venv(venv_args, pip_args)
                venv.install_unmanaged_packages(requirements, pip_args, cooldown_days=cooldown_days)
            except (OSError, PipxError, KeyboardInterrupt):
                # expire the cache so the next run reinstalls the requirements instead of reusing a broken venv
                (venv_dir / _VENV_EXPIRED_FILENAME).touch()
                raise
        _exec_script(venv.python_path, content, app_args, python_args)


def _interpreter_for_script(
    requires_python: str, python: str, fetch_python: FetchPythonOptions, *, python_flag_passed: bool
) -> str:
    if (constraint := unsatisfied_by_interpreter(requires_python, python)) is None:
        return python
    if python_flag_passed:
        msg = (
            f"The script requires Python {requires_python}, which the interpreter chosen with --python does not "
            f"satisfy. Pass a matching --python, or drop --python to let pipx pick one."
        )
        raise PipxError(msg)
    return interpreter_for(constraint, fetch_python)


def _get_temporary_venv_path(  # ruff:ignore[too-many-arguments]  # all inputs feed the cache-key digest; a struct would only relocate them
    requirements: list[str],
    python: str,
    pip_args: list[str],
    venv_args: list[str],
    backend: str,
    *,
    cooldown_days: int | None,
) -> Path:
    # The installer also reads its index, find-links and similar settings from the environment, more of them than a list
    # could track: pip takes PIP_ followed by any option name or alias, in any case, with - or _. So every PIP_*/UV_*
    # variable counts except these, which tune timeouts, retries, parallelism, output and the cache, or are set by
    # `uv run` for its children. pipx compares names as pip sees them: upper case with _ for -.
    prefix, unkeyed = (
        (
            "UV_",
            {
                "UV_CACHE_DIR",
                "UV_CONCURRENT_BUILDS",
                "UV_CONCURRENT_CACHE_READS",
                "UV_CONCURRENT_DOWNLOADS",
                "UV_CONCURRENT_INSTALLS",
                "UV_HTTP_CONNECT_TIMEOUT",
                "UV_HTTP_RETRIES",
                "UV_HTTP_TIMEOUT",
                "UV_NO_CACHE",
                "UV_NO_PROGRESS",
                "UV_REQUEST_TIMEOUT",
                "UV_RUN_RECURSION_DEPTH",
            },
        )
        if backend == UV
        else (
            "PIP_",
            {
                "PIP_CACHE_DIR",
                "PIP_DISABLE_PIP_VERSION_CHECK",
                "PIP_LOCAL_LOG",
                "PIP_LOG",
                "PIP_LOG_FILE",
                "PIP_NO_CACHE_DIR",
                "PIP_NO_COLOR",
                "PIP_NO_INPUT",
                "PIP_NO_PYTHON_VERSION_WARNING",
                "PIP_NO_WARN_CONFLICTS",
                "PIP_NO_WARN_SCRIPT_LOCATION",
                "PIP_PROGRESS_BAR",
                "PIP_QUIET",
                "PIP_RESUME_RETRIES",
                "PIP_RETRIES",
                "PIP_ROOT_USER_ACTION",
                "PIP_TIMEOUT",
                "PIP_VERBOSE",
            },
        )
    )
    # pip and uv (or requests, keyring and platformdirs for them) also read these, and each can change which config file
    # loads, which server answers, which certificate they trust or which credentials they send. HOME and USERPROFILE
    # locate config files too, but another home means another user, whose default pipx home already differs.
    tool_env: Final = {
        "ALL_PROXY",
        "APPDATA",
        "AWS_ACCESS_KEY_ID",
        "AWS_CONFIG_FILE",
        "AWS_DEFAULT_REGION",
        "AWS_PROFILE",
        "AWS_REGION",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_SHARED_CREDENTIALS_FILE",
        "CURL_CA_BUNDLE",
        "HF_TOKEN",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "NETRC",
        "NO_PROXY",
        "PYTHON_KEYRING_BACKEND",
        "PYX_API_KEY",
        "PYX_AUTH_TOKEN",
        "REQUESTS_CA_BUNDLE",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
        "SSL_CLIENT_CERT",
        "SYSTEMDRIVE",
        "WIN_PD_OVERRIDE_APPDATA",
        "WIN_PD_OVERRIDE_COMMON_APPDATA",
        "XDG_CONFIG_DIRS",
        "XDG_CONFIG_HOME",
    }
    installer_env: Final = sorted(
        (name, value)
        for name, value in os.environ.items()
        if ((normalized := name.upper().replace("-", "_")).startswith(prefix) and normalized not in unkeyed)
        or normalized in tool_env
    )
    # Preserve list and field boundaries so different invocations cannot reuse the same digest input. Only the truncated
    # digest leaves this function, so proxy URLs and tokens in the environment never reach the cache path or the logs.
    key: Final = json.dumps([requirements, python, pip_args, venv_args, backend, cooldown_days, installer_env]).encode()
    # other accounts can list the cache, so an unkeyed digest would let them test guesses at a token against a name
    digest: Final = (
        hashlib.sha256(key) if (secret := _cache_secret()) is None else hmac.new(secret, key, hashlib.sha256)
    )
    return Path(paths.CTX.venv_cache) / digest.hexdigest()[:15]


def _cache_secret() -> bytes | None:
    secret_path: Final[Path] = Path(paths.CTX.venv_cache) / _RUN_KEY_FILENAME
    try:
        return _read_cache_secret(secret_path) or _write_cache_secret(secret_path)
    except OSError as error:
        # a cache pipx cannot write to can still serve the entries already in it, so name them the way it always did
        _LOGGER.debug("Cannot use %s (%s), so run cache names are not keyed with a secret", secret_path, error)
        return None


def _read_cache_secret(secret_path: Path) -> bytes | None:
    try:
        with secret_path.open("rb") as file:
            status: Final[os.stat_result] = os.fstat(file.fileno())
            secret: Final[bytes] = file.read(_RUN_KEY_BYTES + 1)
    except FileNotFoundError:
        return None
    # Windows reports no owner and fakes the mode bits; the ACLs of the user profile keep the file private there
    if sys.platform != "win32" and (status.st_uid != os.geteuid() or status.st_mode & 0o077):
        _LOGGER.debug("Replacing %s, which another account owns or can read", secret_path)
        return None
    return secret if len(secret) == _RUN_KEY_BYTES else None


def _write_cache_secret(secret_path: Path) -> bytes:
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    secret: Final[bytes] = secrets.token_bytes(_RUN_KEY_BYTES)
    # mkstemp creates the file with O_EXCL and mode 0600, and linking it into place publishes it whole, so a concurrent
    # first run sees either no secret or the complete one
    descriptor, staged = tempfile.mkstemp(dir=secret_path.parent, prefix=f"{_RUN_KEY_FILENAME}-")
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(secret)
        try:
            os.link(staged, secret_path)
        except FileExistsError:
            if (existing := _read_cache_secret(secret_path)) is not None:
                return existing
            Path(staged).replace(secret_path)
    finally:
        Path(staged).unlink(missing_ok=True)
    return secret


@contextmanager
def _locked_venv_cache(venv_dir: Path) -> Generator[None, None, None]:
    from filelock import Timeout  # ruff:ignore[import-outside-top-level]  # pulls in asyncio, slows startup

    venv_container: Final[VenvContainer] = VenvContainer(paths.CTX.venv_cache)
    for cached_venv_dir in sorted(venv_container.iter_venv_dirs()):
        if cached_venv_dir == venv_dir:
            continue
        # Purging expired venvs is opportunistic housekeeping, so skip any a concurrent run holds rather than block on
        # it; on Windows an in-use cache would keep the lock held for the whole install and stall every other run.
        lock = venv_container.venv_lock(cached_venv_dir)
        try:
            lock.acquire(timeout=0)
        except Timeout:
            continue
        try:
            _remove_expired_venv(cached_venv_dir)
        finally:
            lock.release()
    with venv_container.venv_lock(venv_dir):
        _remove_expired_venv(venv_dir)
        yield


def _remove_expired_venv(venv_dir: Path) -> None:
    if not venv_dir.is_dir():
        return
    age: Final[float] = dt.datetime.now(tz=dt.UTC).timestamp() - venv_dir.stat().st_ctime
    if age > 60 * 60 * 24 * TEMP_VENV_EXPIRATION_THRESHOLD_DAYS or (venv_dir / _VENV_EXPIRED_FILENAME).exists():
        _LOGGER.info("Removing expired venv %s", venv_dir)
        rmdir(venv_dir)


def _prepare_venv_cache(venv: Venv, bin_path: Path | None, *, use_cache: bool, refresh: bool) -> None:
    venv_dir: Final[Path] = venv.root
    if refresh and venv_dir.exists():
        _LOGGER.info("Refreshing cached venv %s", venv_dir)
        rmdir(venv_dir)
    elif not use_cache and (bin_path is None or bin_path.exists()):
        _LOGGER.info("Removing cached venv %s", venv_dir)
        rmdir(venv_dir)


def _exec_script(
    python_path: Path,
    content: str | Path,
    app_args: list[str],
    python_args: list[str],
) -> NoReturn:
    if isinstance(content, Path):
        exec_app([python_path, *python_args, content, *app_args])
    else:
        exec_app([python_path, "-P", *python_args, "-c", content, *app_args])


def run_package(  # ruff:ignore[too-many-arguments]  # mirrors the flat `pipx run` options; a struct would only relocate them
    app: str,
    package_or_url: str,
    dependencies: list[str],
    app_args: list[str],
    python: str,
    *,
    pip_args: list[str],
    venv_args: list[str],
    pypackages: bool,
    verbose: bool,
    use_cache: bool,
    python_args: list[str],
    refresh: bool,
    infer_app_name: bool,
    backend: BackendOptions,
    resolved_backend: str,
    no_path_check: bool,
    cooldown_days: int | None,
) -> NoReturn:
    if not no_path_check and (app_path := which(app)):
        _LOGGER.warning(
            pipx_wrap(
                f"""
                {HAZARD}  {app} is already on your PATH and installed at
                {app_path}. Downloading and running anyway.
                """,
                subsequent_indent=" " * 4,
            )
        )

    app, app_filename = _app_names(app)

    pypackage_bin_path: Final[Path] = get_pypackage_bin_path(app)
    if pypackage_bin_path.exists():
        if python_args:
            msg = "--python-args cannot run applications from __pypackages__."
            raise PipxError(msg)
        _LOGGER.info("Using app in local __pypackages__ directory at '%s'", pypackage_bin_path)
        run_pypackage_bin(pypackage_bin_path, app_args)
    if pypackages:
        msg = f"""
            '--pypackages' flag was passed, but '{pypackage_bin_path}' was
            not found. See https://github.com/cs01/pythonloc to learn how to
            install here, or omit the flag.
            """
        raise PipxError(msg)

    # ``--with`` packages share this venv, so they belong in its key, else ``pipx run foo`` and
    # ``pipx run --with bar foo`` would share one cache dir; the installer resolves local paths against the working
    # directory, so the key does too
    venv_dir: Final[Path] = _get_temporary_venv_path(
        [
            str(script) if (script := local_script(spec)) is not None else resolve_local_path(spec)
            for spec in (package_or_url, *dependencies)
        ],
        python,
        absolute_path_pip_args(pip_args, Path.cwd()),
        venv_args,
        resolved_backend,
        cooldown_days=cooldown_days,
    )

    with _locked_venv_cache(venv_dir):
        venv = Venv(venv_dir, backend=backend)
        if infer_app_name and (cached := venv.pipx_metadata.main_package).package is not None:
            # repeat ``_prepare_venv``'s sole-script fallback, else the cache check below misses and rebuilds the venv
            app, app_filename = _app_names(cached.apps[0] if len(cached.apps) == 1 else cached.package)
        _prepare_venv_cache(venv, venv.bin_path / app_filename, use_cache=use_cache, refresh=refresh)

        if venv.has_app(app, app_filename):
            _LOGGER.info("Reusing cached venv %s", venv_dir)
        else:
            _LOGGER.info("venv location is %s", venv_dir)
            venv, app, app_filename = _prepare_venv(
                venv_dir,
                package_or_url,
                app,
                app_filename,
                python,
                pip_args=pip_args,
                venv_args=venv_args,
                use_cache=use_cache,
                verbose=verbose,
                infer_app_name=infer_app_name,
                backend=backend,
                cooldown_days=cooldown_days,
                dependencies=dependencies,
            )
        venv.run_app(app, app_filename, app_args, python_args=python_args)


def _app_names(app: str) -> tuple[str, str]:
    if not WINDOWS:
        return app, app
    # apps recorded in the venv metadata carry the .exe stub suffix, so drop it before re-appending
    name: Final[str] = app[: -len(".exe")] if app.lower().endswith(".exe") else app
    _LOGGER.info("Assuming app is %r (Windows only)", app_filename := f"{name}.exe")
    return name, app_filename


def _prepare_venv(  # ruff:ignore[too-many-arguments]  # mirrors the flat run/install option set for one temporary venv
    venv_dir: Path,
    package_or_url: str,
    app: str,
    app_filename: str,
    python: str,
    *,
    pip_args: list[str],
    venv_args: list[str],
    use_cache: bool,
    verbose: bool,
    infer_app_name: bool,
    backend: BackendOptions,
    cooldown_days: int | None,
    dependencies: Sequence[str],
) -> tuple[Venv, str, str]:
    venv: Final[Venv] = Venv(venv_dir, python=python, verbose=verbose, backend=backend)
    venv.check_upgrade_shared_libs(pip_args=pip_args, verbose=verbose)

    if venv.pipx_metadata.main_package.package is not None:
        package_name = venv.pipx_metadata.main_package.package
    else:
        # a spec without a distribution name costs a throwaway venv here, so resolve it on the requested backend
        package_name = package_name_from_spec(
            package_or_url,
            python,
            pip_args=pip_args,
            verbose=verbose,
            backend=backend,
            cooldown_days=cooldown_days,
        )

    if infer_app_name:
        app, app_filename = _app_names(package_name)

    try:
        venv.create_venv(venv_args, pip_args, override_shared=package_name == "pip")
        venv.install_package(
            package_name=package_name,
            package_or_url=package_or_url,
            pip_args=pip_args,
            exposure=ExposureOptions(),
            is_main_package=True,
            cooldown_days=cooldown_days,
            # resolved with the app so a pin or cap on one of its dependencies takes effect
            extra_requirements=dependencies,
        )
    except (OSError, PipxError, KeyboardInterrupt):
        # a half-built venv has no record of its backend, so the next run must start from scratch; a missing app below
        # leaves a complete venv the next correct command can reuse
        if venv_dir.is_dir():
            (venv_dir / _VENV_EXPIRED_FILENAME).touch()
        raise

    if not venv.has_app(app, app_filename):
        apps: Final[list[str]] = venv.pipx_metadata.main_package.apps
        if app == package_name and len(apps) == 1:
            app, app_filename = _app_names(apps[0])
            print(f"NOTE: running app {app!r} from {package_name!r}")  # ruff:ignore[print]  # user-facing CLI output
        else:
            app_lines: Final[str] = "\n    ".join(
                f"{name} - usage: 'pipx run --spec {redact_url_credentials(package_or_url)} {name} [arguments?]'"
                for name in apps
            )
            msg = (
                f"'{app}' executable script not found in package '{package_name}'.\n"
                f"Available executable scripts:\n    {app_lines}"
            )
            raise PipxError(msg, wrap_message=False)

    if not use_cache:
        # the next run's cache sweep removes a venv built without the cache
        (venv_dir / _VENV_EXPIRED_FILENAME).touch()

    return venv, app, app_filename


__all__ = [
    "maybe_script_content",
    "run",
    "run_package",
]
