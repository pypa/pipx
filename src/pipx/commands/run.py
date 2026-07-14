import datetime
import hashlib
import logging
import re
import sys
import time
import urllib.parse
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from shutil import which
from typing import Final, NoReturn

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from pipx import paths
from pipx.backends import UV, resolve_backend_name
from pipx.commands.common import package_name_from_spec
from pipx.commands.inject import inject_dep
from pipx.commands.run_uv import run_script_via_uv_run, run_via_uv_tool_run
from pipx.constants import TEMP_VENV_EXPIRATION_THRESHOLD_DAYS, WINDOWS
from pipx.emojis import hazard
from pipx.util import (
    PipxError,
    exec_app,
    get_pypackage_bin_path,
    pipx_wrap,
    rmdir,
    run_pypackage_bin,
)
from pipx.venv import Venv, VenvContainer

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

_VENV_EXPIRED_FILENAME: Final[str] = "pipx_expired_venv"
_VCS_SCHEMES: Final[frozenset[str]] = frozenset({"bzr", "git", "hg", "svn"})

_APP_NOT_FOUND_ERROR_MESSAGE: Final[str] = """\
'{app}' executable script not found in package '{package_name}'.
Available executable scripts:
    {app_lines}"""


def maybe_script_content(app: str, is_path: bool) -> str | Path | None:
    """If the app is a script, return its content.
    Return None if it should be treated as a package name."""

    # Look for a local file first.
    app_path = Path(app)
    if app_path.is_file():
        return app_path
    # In case it's a named pipe, read it out to pass to the interpreter
    if app_path.is_fifo():
        return app_path.read_text(encoding="utf-8")

    if is_path:
        raise PipxError(f"The specified path {app} does not exist")

    # Check for a URL
    if urllib.parse.urlparse(app).scheme:
        if _is_vcs_url(app):
            return None
        if not app.endswith(".py"):
            raise PipxError(
                """
                pipx will only execute apps from the internet directly if they
                end with '.py'. To run a package from another URL, use
                'pipx run --spec URL BINARY'.
                """
            )
        _LOGGER.info("Detected url. Downloading and executing as a Python file.")

        return _http_get_request(app)

    # Otherwise, it's a package
    return None


def run_script(
    content: str | Path,
    app_args: list[str],
    python: str,
    pip_args: list[str],
    venv_args: list[str],
    verbose: bool,
    use_cache: bool,
    *,
    python_args: list[str],
    refresh: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
    resolved_backend: str | None = None,
    script_source: Path | None = None,
    dependencies: list[str] | None = None,
    cooldown_days: int | None = None,
) -> NoReturn:
    requirements = _get_requirements_from_script(content)

    if dependencies:
        if requirements is None:
            # Plain scripts have nowhere to record extra requirements; the pip path
            # silently dropped ``--with`` here, but a clear error is better.
            raise PipxError(
                "--with packages can only be applied to scripts with PEP 723 inline metadata "
                "(`# /// script` block). Add the dependencies to the script's metadata or run "
                "via `pipx run --spec`."
            )
        requirements = [*requirements, *dependencies]

    if resolved_backend == UV and requirements is not None and not python_args:
        if script_source is not None:
            run_script_via_uv_run(
                script_path=script_source,
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
        # URL / named-pipe content has no on-disk path for ``uv run --script``;
        # warn so users on ``--backend uv`` notice they lose uv's cache and
        # Python-managing semantics for this run.
        _LOGGER.warning(
            pipx_wrap(
                f"""
                {hazard}  Script content is not a local file; building a
                pipx-managed venv via the uv backend instead of `uv run
                --script`. The uv cache and uv-managed Python features
                will not apply to this run.
                """,
                subsequent_indent=" " * 4,
            )
        )

    if not requirements:
        _exec_script(Path(python), content, app_args, python_args)

    # Note that the environment name is based on the identified
    # requirements, and *not* on the script name. This is deliberate, as
    # it ensures that two scripts with the same requirements can use the
    # same environment, which means fewer environments need to be
    # managed. The requirements are normalised (in
    # _get_requirements_from_script), so that irrelevant differences in
    # whitespace, and similar, don't prevent environment sharing.
    venv_dir = _get_temporary_venv_path(
        requirements,
        python,
        pip_args,
        venv_args,
        resolved_backend or "pip",
        cooldown_days,
    )
    with _locked_venv_cache(venv_dir):
        venv = Venv(venv_dir, backend=backend, env_backend=env_backend)
        _prepare_venv_cache(venv, None, use_cache, refresh=refresh)
        if venv_dir.exists():
            _LOGGER.info(f"Reusing cached venv {venv_dir}")
        else:
            venv = Venv(venv_dir, python=python, verbose=verbose, backend=backend, env_backend=env_backend)
            venv.check_upgrade_shared_libs(pip_args=pip_args, verbose=verbose)
            venv.create_venv(venv_args, pip_args)
            try:
                venv.install_unmanaged_packages(requirements, pip_args, cooldown_days=cooldown_days)
            except (OSError, PipxError, KeyboardInterrupt):
                # Package installation failed, so mark the cache as expired.
                # This ensures an attempt is made to re-install requirements
                # when `pipx run` is next executed, rather than just failing.
                (venv_dir / _VENV_EXPIRED_FILENAME).touch()
                raise
        _exec_script(venv.python_path, content, app_args, python_args)


def _exec_script(
    python_path: Path,
    content: str | Path,
    app_args: list[str],
    python_args: list[str],
) -> NoReturn:
    if isinstance(content, Path):
        exec_app([python_path, *python_args, content, *app_args])
    else:
        exec_app([python_path, *python_args, "-c", content, *app_args])


def run_package(
    app: str,
    package_or_url: str,
    dependencies: list[str],
    app_args: list[str],
    python: str,
    pip_args: list[str],
    venv_args: list[str],
    pypackages: bool,
    verbose: bool,
    use_cache: bool,
    *,
    python_args: list[str],
    refresh: bool = False,
    infer_app_name: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
    resolved_backend: str | None = None,
    no_path_check: bool = False,
    cooldown_days: int | None = None,
) -> NoReturn:
    if not no_path_check and (app_path := which(app)):
        _LOGGER.warning(
            pipx_wrap(
                f"""
                {hazard}  {app} is already on your PATH and installed at
                {app_path}. Downloading and running anyway.
                """,
                subsequent_indent=" " * 4,
            )
        )

    if WINDOWS:
        app_filename = f"{app}.exe"
        _LOGGER.info(f"Assuming app is {app_filename!r} (Windows only)")
    else:
        app_filename = app

    pypackage_bin_path = get_pypackage_bin_path(app)
    if pypackage_bin_path.exists():
        if python_args:
            raise PipxError("--python-args cannot run applications from __pypackages__.")
        _LOGGER.info(f"Using app in local __pypackages__ directory at '{pypackage_bin_path}'")
        run_pypackage_bin(pypackage_bin_path, app_args)
    if pypackages:
        raise PipxError(
            f"""
            '--pypackages' flag was passed, but '{pypackage_bin_path}' was
            not found. See https://github.com/cs01/pythonloc to learn how to
            install here, or omit the flag.
            """
        )

    venv_dir = _get_temporary_venv_path(
        [package_or_url],
        python,
        pip_args,
        venv_args,
        resolved_backend or "pip",
        cooldown_days,
    )

    with _locked_venv_cache(venv_dir):
        venv = Venv(venv_dir, backend=backend, env_backend=env_backend)
        if infer_app_name and venv.pipx_metadata.main_package.package is not None:
            app = venv.pipx_metadata.main_package.package
            app_filename = f"{app}.exe" if WINDOWS else app
        bin_path = venv.bin_path / app_filename
        _prepare_venv_cache(venv, bin_path, use_cache, refresh=refresh)

        if venv.has_app(app, app_filename):
            _LOGGER.info(f"Reusing cached venv {venv_dir}")
        else:
            _LOGGER.info(f"venv location is {venv_dir}")
            venv, app, app_filename = _prepare_venv(
                Path(venv_dir),
                package_or_url,
                app,
                app_filename,
                python,
                pip_args,
                venv_args,
                use_cache,
                verbose,
                infer_app_name=infer_app_name,
                backend=backend,
                env_backend=env_backend,
                cooldown_days=cooldown_days,
            )

        for dependency in dependencies:
            inject_dep(
                venv_dir=venv_dir,
                package_name=None,
                package_spec=dependency,
                pip_args=pip_args,
                verbose=verbose,
                include_apps=False,
                include_dependencies=False,
                include_apps_from=(),
                force=False,
                backend=backend,
                env_backend=env_backend,
                cooldown_days=cooldown_days,
            )
        venv.run_app(app, app_filename, app_args, python_args=python_args)


def run(
    app: str,
    spec: str | None,
    dependencies: list[str],
    is_path: bool,
    app_args: list[str],
    python: str,
    pip_args: list[str],
    venv_args: list[str],
    pypackages: bool,
    verbose: bool,
    use_cache: bool,
    *,
    python_args: list[str],
    refresh: bool = False,
    no_path_check: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
    cooldown_days: int | None = None,
) -> NoReturn:
    """Installs venv to temporary dir (or reuses cache), then runs app from
    package
    """

    package_name: Final[str] = _package_name_from_app(app, inferred=spec is None)

    # ``resolved_backend`` only decides ROUTING (uv tool run vs Venv); cli/env
    # stay separate when we hand off so the Venv's source-attribution stays right.
    resolved_backend, _ = resolve_backend_name(cli_value=backend, env_value=env_backend)
    use_uvx = resolved_backend == UV and not pypackages and not python_args

    content = None if spec is not None else maybe_script_content(app, is_path)
    if content is not None:
        run_script(
            content,
            app_args,
            python,
            pip_args,
            venv_args,
            verbose,
            use_cache,
            refresh=refresh,
            backend=backend,
            env_backend=env_backend,
            resolved_backend=resolved_backend,
            script_source=Path(app) if isinstance(content, Path) else None,
            dependencies=dependencies,
            cooldown_days=cooldown_days,
            python_args=python_args,
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
            cooldown_days=cooldown_days,
        )
    else:
        package_or_url = spec if spec is not None else app
        run_package(
            package_name,
            package_or_url,
            dependencies,
            app_args,
            python,
            pip_args,
            venv_args,
            pypackages,
            verbose,
            use_cache,
            refresh=refresh,
            infer_app_name=spec is None and _is_vcs_url(app),
            backend=backend,
            env_backend=env_backend,
            resolved_backend=resolved_backend,
            no_path_check=no_path_check,
            cooldown_days=cooldown_days,
            python_args=python_args,
        )


def _package_name_from_app(app: str, *, inferred: bool) -> str:
    try:
        package_name = Requirement(app).name
    except InvalidRequirement:
        return app
    return canonicalize_name(package_name) if inferred else package_name


def _prepare_venv(
    venv_dir: Path,
    package_or_url: str,
    app: str,
    app_filename: str,
    python: str,
    pip_args: list[str],
    venv_args: list[str],
    use_cache: bool,
    verbose: bool,
    *,
    infer_app_name: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
    cooldown_days: int | None = None,
) -> tuple[Venv, str, str]:
    venv = Venv(venv_dir, python=python, verbose=verbose, backend=backend, env_backend=env_backend)
    venv.check_upgrade_shared_libs(pip_args=pip_args, verbose=verbose)

    if venv.pipx_metadata.main_package.package is not None:
        package_name = venv.pipx_metadata.main_package.package
    else:
        package_name = package_name_from_spec(
            package_or_url,
            python,
            pip_args=pip_args,
            verbose=verbose,
            cooldown_days=cooldown_days,
        )

    if infer_app_name:
        app = package_name
        app_filename = f"{app}.exe" if WINDOWS else app

    override_shared = package_name == "pip"

    venv.create_venv(venv_args, pip_args, override_shared)
    venv.install_package(
        package_name=package_name,
        package_or_url=package_or_url,
        pip_args=pip_args,
        include_dependencies=False,
        include_apps_from=(),
        include_apps=True,
        is_main_package=True,
        cooldown_days=cooldown_days,
    )

    if not venv.has_app(app, app_filename):
        apps = venv.pipx_metadata.main_package.apps

        # If there's a single app inside the package, run that by default
        if app == package_name and len(apps) == 1:
            app = apps[0]
            print(f"NOTE: running app {app!r} from {package_name!r}")
            if WINDOWS:
                app_filename = f"{app}.exe"
                _LOGGER.info(f"Assuming app is {app_filename!r} (Windows only)")
            else:
                app_filename = app
        else:
            all_apps = (f"{a} - usage: 'pipx run --spec {package_or_url} {a} [arguments?]'" for a in apps)
            raise PipxError(
                _APP_NOT_FOUND_ERROR_MESSAGE.format(
                    app=app,
                    package_name=package_name,
                    app_lines="\n    ".join(all_apps),
                ),
                wrap_message=False,
            )

    if not use_cache:
        # Let future _remove_all_expired_venvs know to remove this
        (venv_dir / _VENV_EXPIRED_FILENAME).touch()

    return venv, app, app_filename


def _is_vcs_url(value: str) -> bool:
    scheme = urllib.parse.urlparse(value).scheme
    vcs, separator, _ = scheme.partition("+")
    return bool(separator) and vcs in _VCS_SCHEMES


def _get_temporary_venv_path(
    requirements: list[str],
    python: str,
    pip_args: list[str],
    venv_args: list[str],
    backend: str,
    cooldown_days: int | None,
) -> Path:
    """Hash venv-affecting inputs to a deterministic cache path.

    ``backend`` is part of the key so pip- and uv-backed temp venvs for the
    same package coexist instead of stomping on each other.
    """
    digest = hashlib.sha256()
    digest.update("".join(requirements).encode())
    digest.update(python.encode())
    digest.update("".join(pip_args).encode())
    digest.update("".join(venv_args).encode())
    digest.update(backend.encode())
    digest.update(f"{cooldown_days=}".encode())
    venv_folder_name = digest.hexdigest()[:15]  # 15 chosen arbitrarily
    return Path(paths.ctx.venv_cache) / venv_folder_name


def _is_temporary_venv_expired(venv_dir: Path) -> bool:
    created_time_sec = venv_dir.stat().st_ctime
    current_time_sec = time.mktime(datetime.datetime.now().timetuple())
    age = current_time_sec - created_time_sec
    expiration_threshold_sec = 60 * 60 * 24 * TEMP_VENV_EXPIRATION_THRESHOLD_DAYS
    return age > expiration_threshold_sec or (venv_dir / _VENV_EXPIRED_FILENAME).exists()


@contextmanager
def _locked_venv_cache(venv_dir: Path) -> Iterator[None]:
    venv_container: Final[VenvContainer] = VenvContainer(paths.ctx.venv_cache)
    for cached_venv_dir in sorted(venv_container.iter_venv_dirs()):
        if cached_venv_dir == venv_dir:
            continue
        with venv_container.venv_lock(cached_venv_dir):
            _remove_expired_venv(cached_venv_dir)
    with venv_container.venv_lock(venv_dir):
        _remove_expired_venv(venv_dir)
        yield


def _prepare_venv_cache(venv: Venv, bin_path: Path | None, use_cache: bool, *, refresh: bool = False) -> None:
    venv_dir = venv.root
    if refresh and venv_dir.exists():
        _LOGGER.info(f"Refreshing cached venv {venv_dir!s}")
        rmdir(venv_dir)
    elif not use_cache and (bin_path is None or bin_path.exists()):
        _LOGGER.info(f"Removing cached venv {venv_dir!s}")
        rmdir(venv_dir)


def _remove_expired_venv(venv_dir: Path) -> None:
    if venv_dir.is_dir() and _is_temporary_venv_expired(venv_dir):
        _LOGGER.info(f"Removing expired venv {venv_dir!s}")
        rmdir(venv_dir)


def _http_get_request(url: str) -> str:
    try:
        res = urllib.request.urlopen(url)
        charset = res.headers.get_content_charset() or "utf-8"
        return res.read().decode(charset)
    except Exception as e:
        _LOGGER.debug("Uncaught Exception:", exc_info=True)
        raise PipxError(str(e)) from e


# Pattern from PEP 723 / inline script metadata spec.
_INLINE_SCRIPT_METADATA: Final[re.Pattern[str]] = re.compile(
    r"""
    ^\#\ ///\ (?P<type>[a-zA-Z0-9-]+)$ \s   # opening fence: ``# /// <type>``
    (?P<content> (^\#(|\ .*)$ \s)+ )        # body: lines starting with ``#`` or ``# ``
    ^\#\ ///$                               # closing fence: ``# ///``
    """,
    re.VERBOSE | re.MULTILINE,
)


def _get_requirements_from_script(content: str | Path) -> list[str] | None:
    """
    Supports inline script metadata.
    """

    if isinstance(content, Path):
        content = content.read_text(encoding="utf-8")

    name = "script"

    # Windows is currently getting un-normalized line endings, so normalize
    content = content.replace("\r\n", "\n")

    matches = [m for m in _INLINE_SCRIPT_METADATA.finditer(content) if m.group("type") == name]

    if not matches:
        pyproject_matches = [m for m in _INLINE_SCRIPT_METADATA.finditer(content) if m.group("type") == "pyproject"]
        if pyproject_matches:
            _LOGGER.error(
                pipx_wrap(
                    f"""
                    {hazard}  Using old form of requirements table. Use updated PEP
                    723 syntax by replacing `# /// pyproject` with `# /// script`
                    and `run.dependencies` (or `run.requirements`) with
                    `dependencies`.
                    """,
                    subsequent_indent=" " * 4,
                )
            )
            raise ValueError("Old 'pyproject' table found")
        return None

    if len(matches) > 1:
        raise ValueError(f"Multiple {name} blocks found")

    content = "".join(
        line[2:] if line.startswith("# ") else line[1:] for line in matches[0].group("content").splitlines(keepends=True)
    )

    pyproject = tomllib.loads(content)

    requirements = []
    for requirement in pyproject.get("dependencies", []):
        try:
            parsed_requirement = Requirement(requirement)
        except InvalidRequirement as exc:
            raise PipxError(f"Invalid requirement {requirement}: {exc}") from exc

        # Use the normalised form of the requirement
        requirements.append(str(parsed_requirement))

    return requirements


__all__ = [
    "maybe_script_content",
    "run",
    "run_package",
    "run_script",
]
