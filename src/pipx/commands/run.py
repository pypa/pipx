import datetime
import hashlib
import logging
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from shutil import which
from typing import List, NoReturn, Optional, Union

from packaging.requirements import InvalidRequirement, Requirement

from pipx import paths
from pipx.commands.common import package_name_from_spec
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
from pipx.venv import Venv

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

logger = logging.getLogger(__name__)


VENV_EXPIRED_FILENAME = "pipx_expired_venv"

APP_NOT_FOUND_ERROR_MESSAGE = """\
'{app}' executable script not found in package '{package_name}'.
Available executable scripts:
    {app_lines}"""


def maybe_script_content(app: str, is_path: bool) -> Optional[Union[str, Path]]:
    # If the app is a script, return its content.
    # Return None if it should be treated as a package name.

    # Look for a local file first.
    app_path = Path(app)
    if app_path.is_file():
        return app_path
    elif is_path:
        raise PipxError(f"The specified path {app} does not exist")

    # Check for a URL
    if urllib.parse.urlparse(app).scheme:
        if not app.endswith(".py"):
            raise PipxError(
                """
                pipx will only execute apps from the internet directly if they
                end with '.py'. To run from an SVN, try pipx --spec URL BINARY
                """
            )
        logger.info("Detected url. Downloading and executing as a Python file.")

        return _http_get_request(app)

    # Otherwise, it's a package
    return None


def run_script(
    content: Union[str, Path],
    app_args: List[str],
    python: str,
    pip_args: List[str],
    venv_args: List[str],
    verbose: bool,
    use_cache: bool,
) -> NoReturn:
    requirements = _get_requirements_from_script(content)
    if requirements is None:
        python_path = Path(python)
    else:
        # Note that the environment name is based on the identified
        # requirements, and *not* on the script name. This is deliberate, as
        # it ensures that two scripts with the same requirements can use the
        # same environment, which means fewer environments need to be
        # managed. The requirements are normalised (in
        # _get_requirements_from_script), so that irrelevant differences in
        # whitespace, and similar, don't prevent environment sharing.
        venv_dir = _get_temporary_venv_path(requirements, python, pip_args, venv_args)
        venv = Venv(venv_dir)
        _prepare_venv_cache(venv, None, use_cache)
        if venv_dir.exists():
            logger.info(f"Reusing cached venv {venv_dir}")
        else:
            venv = Venv(venv_dir, python=python, verbose=verbose)
            venv.check_upgrade_shared_libs(pip_args=pip_args, verbose=verbose)
            venv.create_venv(venv_args, pip_args)
            venv.install_unmanaged_packages(requirements, pip_args)
        python_path = venv.python_path

    if isinstance(content, Path):
        exec_app([python_path, content, *app_args])
    else:
        exec_app([python_path, "-c", content, *app_args])


def run_package(
    app: str,
    package_or_url: str,
    app_args: List[str],
    python: str,
    pip_args: List[str],
    venv_args: List[str],
    pypackages: bool,
    verbose: bool,
    use_cache: bool,
) -> NoReturn:
    if which(app):
        logger.warning(
            pipx_wrap(
                f"""
                {hazard}  {app} is already on your PATH and installed at
                {which(app)}. Downloading and running anyway.
                """,
                subsequent_indent=" " * 4,
            )
        )

    if WINDOWS:
        app_filename = f"{app}.exe"
        logger.info(f"Assuming app is {app_filename!r} (Windows only)")
    else:
        app_filename = app

    pypackage_bin_path = get_pypackage_bin_path(app)
    if pypackage_bin_path.exists():
        logger.info(f"Using app in local __pypackages__ directory at '{pypackage_bin_path}'")
        run_pypackage_bin(pypackage_bin_path, app_args)
    if pypackages:
        raise PipxError(
            f"""
            '--pypackages' flag was passed, but '{pypackage_bin_path}' was
            not found. See https://github.com/cs01/pythonloc to learn how to
            install here, or omit the flag.
            """
        )

    venv_dir = _get_temporary_venv_path([package_or_url], python, pip_args, venv_args)

    venv = Venv(venv_dir)
    bin_path = venv.bin_path / app_filename
    _prepare_venv_cache(venv, bin_path, use_cache)

    if venv.has_app(app, app_filename):
        logger.info(f"Reusing cached venv {venv_dir}")
        venv.run_app(app, app_filename, app_args)
    else:
        logger.info(f"venv location is {venv_dir}")
        _download_and_run(
            Path(venv_dir),
            package_or_url,
            app,
            app_filename,
            app_args,
            python,
            pip_args,
            venv_args,
            use_cache,
            verbose,
        )


def run(
    app: str,
    spec: str,
    is_path: bool,
    app_args: List[str],
    python: str,
    pip_args: List[str],
    venv_args: List[str],
    pypackages: bool,
    verbose: bool,
    use_cache: bool,
) -> NoReturn:
    """Installs venv to temporary dir (or reuses cache), then runs app from
    package
    """

    # For any package, we need to just use the name
    try:
        package_name = Requirement(app).name
    except InvalidRequirement:
        # Raw URLs to scripts are supported, too, so continue if
        # we can't parse this as a package
        package_name = app

    content = None if spec is not None else maybe_script_content(app, is_path)
    if content is not None:
        run_script(content, app_args, python, pip_args, venv_args, verbose, use_cache)
    else:
        package_or_url = spec if spec is not None else app
        run_package(
            package_name,
            package_or_url,
            app_args,
            python,
            pip_args,
            venv_args,
            pypackages,
            verbose,
            use_cache,
        )


def _download_and_run(
    venv_dir: Path,
    package_or_url: str,
    app: str,
    app_filename: str,
    app_args: List[str],
    python: str,
    pip_args: List[str],
    venv_args: List[str],
    use_cache: bool,
    verbose: bool,
) -> NoReturn:
    venv = Venv(venv_dir, python=python, verbose=verbose)
    venv.check_upgrade_shared_libs(pip_args=pip_args, verbose=verbose)

    if venv.pipx_metadata.main_package.package is not None:
        package_name = venv.pipx_metadata.main_package.package
    else:
        package_name = package_name_from_spec(package_or_url, python, pip_args=pip_args, verbose=verbose)

    override_shared = package_name == "pip"

    venv.create_venv(venv_args, pip_args, override_shared)
    venv.install_package(
        package_name=package_name,
        package_or_url=package_or_url,
        pip_args=pip_args,
        include_dependencies=False,
        include_apps=True,
        is_main_package=True,
    )

    if not venv.has_app(app, app_filename):
        apps = venv.pipx_metadata.main_package.apps

        # If there's a single app inside the package, run that by default
        if app == package_name and len(apps) == 1:
            app = apps[0]
            print(f"NOTE: running app {app!r} from {package_name!r}")
            if WINDOWS:
                app_filename = f"{app}.exe"
                logger.info(f"Assuming app is {app_filename!r} (Windows only)")
            else:
                app_filename = app
        else:
            all_apps = (f"{a} - usage: 'pipx run --spec {package_or_url} {a} [arguments?]'" for a in apps)
            raise PipxError(
                APP_NOT_FOUND_ERROR_MESSAGE.format(
                    app=app,
                    package_name=package_name,
                    app_lines="\n    ".join(all_apps),
                ),
                wrap_message=False,
            )

    if not use_cache:
        # Let future _remove_all_expired_venvs know to remove this
        (venv_dir / VENV_EXPIRED_FILENAME).touch()

    venv.run_app(app, app_filename, app_args)


def _get_temporary_venv_path(requirements: List[str], python: str, pip_args: List[str], venv_args: List[str]) -> Path:
    """Computes deterministic path using hashing function on arguments relevant
    to virtual environment's end state. Arguments used should result in idempotent
    virtual environment. (i.e. args passed to app aren't relevant, but args
    passed to venv creation are.)
    """
    m = hashlib.sha256()
    m.update("".join(requirements).encode())
    m.update(python.encode())
    m.update("".join(pip_args).encode())
    m.update("".join(venv_args).encode())
    venv_folder_name = m.hexdigest()[:15]  # 15 chosen arbitrarily
    return Path(paths.ctx.venv_cache) / venv_folder_name


def _is_temporary_venv_expired(venv_dir: Path) -> bool:
    created_time_sec = venv_dir.stat().st_ctime
    current_time_sec = time.mktime(datetime.datetime.now().timetuple())
    age = current_time_sec - created_time_sec
    expiration_threshold_sec = 60 * 60 * 24 * TEMP_VENV_EXPIRATION_THRESHOLD_DAYS
    return age > expiration_threshold_sec or (venv_dir / VENV_EXPIRED_FILENAME).exists()


def _prepare_venv_cache(venv: Venv, bin_path: Optional[Path], use_cache: bool) -> None:
    venv_dir = venv.root
    if not use_cache and (bin_path is None or bin_path.exists()):
        logger.info(f"Removing cached venv {venv_dir!s}")
        rmdir(venv_dir)
    _remove_all_expired_venvs()


def _remove_all_expired_venvs() -> None:
    for venv_dir in Path(paths.ctx.venv_cache).iterdir():
        if _is_temporary_venv_expired(venv_dir):
            logger.info(f"Removing expired venv {venv_dir!s}")
            rmdir(venv_dir)


def _http_get_request(url: str) -> str:
    try:
        res = urllib.request.urlopen(url)
        charset = res.headers.get_content_charset() or "utf-8"
        return res.read().decode(charset)
    except Exception as e:
        logger.debug("Uncaught Exception:", exc_info=True)
        raise PipxError(str(e)) from e


# This regex comes from the inline script metadata spec
INLINE_SCRIPT_METADATA = re.compile(r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$")


def _get_requirements_from_script(content: Union[str, Path]) -> Optional[List[str]]:
    """
    Supports inline script metadata.
    """

    if isinstance(content, Path):
        content = content.read_text(encoding="utf-8")

    name = "script"

    # Windows is currently getting un-normalized line endings, so normalize
    content = content.replace("\r\n", "\n")

    matches = [m for m in INLINE_SCRIPT_METADATA.finditer(content) if m.group("type") == name]

    if not matches:
        pyproject_matches = [m for m in INLINE_SCRIPT_METADATA.finditer(content) if m.group("type") == "pyproject"]
        if pyproject_matches:
            logger.error(
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
        # Validate the requirement
        try:
            req = Requirement(requirement)
        except InvalidRequirement as e:
            raise PipxError(f"Invalid requirement {requirement}: {e}") from e

        # Use the normalised form of the requirement
        requirements.append(str(req))

    return requirements
