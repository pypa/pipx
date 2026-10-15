from __future__ import annotations

__lazy_modules__ = ["configparser", "pathlib", "pipx", "pipx.fanout", "pipx.interpreter", "pipx.util", "threading"]

import datetime as dt
import logging
import os
import time
from configparser import ConfigParser
from configparser import Error as ConfigParserError
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING, Final

from pipx import paths
from pipx.animate import animate
from pipx.constants import WINDOWS
from pipx.emojis import strtobool
from pipx.fanout import in_turn
from pipx.interpreter import get_default_python
from pipx.util import (
    PipxError,
    get_site_packages,
    get_venv_paths,
    run_subprocess,
    subprocess_post_check,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from subprocess import CompletedProcess

    from filelock import BaseFileLock

logger = logging.getLogger(__name__)


SHARED_LIBS_MAX_AGE_SEC: Final[float] = dt.timedelta(days=30).total_seconds()
DISABLE_SHARED_LIBS_AUTO_UPGRADE: Final[str] = "PIPX_DISABLE_SHARED_LIBS_AUTO_UPGRADE"
_SKIP_MAINTENANCE: Final[ContextVar[bool]] = ContextVar("skip_maintenance", default=False)


def shared_libs_auto_upgrade_disabled() -> bool:
    return _SKIP_MAINTENANCE.get() or strtobool(os.getenv(DISABLE_SHARED_LIBS_AUTO_UPGRADE, "0"))


@contextmanager
def skip_shared_libs_maintenance(*, enabled: bool) -> Generator[None, None, None]:
    token = _SKIP_MAINTENANCE.set(enabled)
    try:
        yield
    finally:
        _SKIP_MAINTENANCE.reset(token)


def _venv_python_is_valid(python_path: Path) -> bool:
    """Check if a venv's Python is valid and its underlying interpreter exists.

    On Windows, a venv's python.exe is a wrapper that uses pyvenv.cfg to find
    the actual Python installation. If the original Python is uninstalled,
    the wrapper exists but cannot execute. This function checks that the
    underlying interpreter referenced in pyvenv.cfg still exists.
    """
    if not WINDOWS:
        return True

    pyvenv_cfg = python_path.parent.parent / "pyvenv.cfg"
    if not pyvenv_cfg.is_file():
        return True

    config = ConfigParser()
    try:
        # ConfigParser needs a section header, pyvenv.cfg doesn't have one
        config.read_string("[DEFAULT]\n" + pyvenv_cfg.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ConfigParserError):
        # If we can't read pyvenv.cfg, assume the venv is valid
        return True

    home = config.get("DEFAULT", "home", fallback=None)
    if home:
        # The home path points to the directory containing the original python.exe
        original_python = Path(home) / "python.exe"
        if not original_python.is_file():
            logger.info("Shared libs venv references a missing Python interpreter: %s", original_python)
            return False

    return True


class _SharedLibs:
    def __init__(self) -> None:
        self._site_packages: dict[Path, list[Path]] = {}
        self._is_valid: bool | None = None
        self._rebuilds = 0
        # fan-out tasks check the validity from several threads while one of them may rebuild the shared venv
        self._lock: Final[RLock] = RLock()
        self.has_been_updated_this_run = False
        self.has_been_logged_this_run = False

    @property
    def root(self) -> Path:
        return paths.ctx.shared_libs

    @property
    def bin_path(self) -> Path:
        bin_path, _, _ = get_venv_paths(self.root)
        return bin_path

    @property
    def python_path(self) -> Path:
        _, python_path, _ = get_venv_paths(self.root)
        return python_path

    @property
    def man_path(self) -> Path:
        _, _, man_path = get_venv_paths(self.root)
        return man_path

    @property
    def pip_path(self) -> Path:
        return self.bin_path / ("pip" if not WINDOWS else "pip.exe")

    @property
    def site_packages(self) -> list[Path]:
        if self.python_path not in self._site_packages:
            self._site_packages[self.python_path] = get_site_packages(self.python_path)

        return self._site_packages[self.python_path]

    def create(self, pip_args: list[str], *, verbose: bool = False, reinstall_pip: bool | None = None) -> None:
        with in_turn(lambda: self._is_valid is True), self._lock, self._maintenance_lock():
            self._create(pip_args, verbose=verbose, reinstall_pip=reinstall_pip)

    def run_repairing_pip(
        self, run: Callable[[], CompletedProcess[str]], *, pip_args: list[str], verbose: bool
    ) -> CompletedProcess[str]:
        # A failed pip run only implicates the shared pip when pip itself no longer imports, so ordinary install
        # failures (an unresolvable requirement, a build error) come back untouched.
        rebuilds: Final[int] = self._rebuilds
        if (process := run()).returncode and self._rebuild_if_pip_broken(rebuilds, pip_args=pip_args, verbose=verbose):
            return run()
        return process

    def _rebuild_if_pip_broken(self, rebuilds: int, *, pip_args: list[str], verbose: bool) -> bool:
        # under the lock a rebuild holds: pip imports again midway through one, which would pass for an ordinary failure
        with self._lock:
            if self._rebuilds == rebuilds and self._pip_imports():
                return False
        # fan-out tasks fail together on a broken pip; the first in task order rebuilds it and the others retry on
        # that, as when running one after another, instead of each clearing the venv the others are retrying from
        with in_turn(lambda: self._rebuilds != rebuilds), self._lock, self._maintenance_lock():
            # rechecked as another pipx process may have rebuilt it while this one waited for the lock
            if self._rebuilds == rebuilds and not self._pip_imports():
                logger.warning("pip in the shared libraries at %s does not import, rebuilding them", self.root)
                self._is_valid = False
                self._create(pip_args, verbose=verbose)
                self._rebuilds += 1
        return True

    def _pip_imports(self) -> bool:
        return (
            self.python_path.is_file()
            and not run_subprocess(
                [self.python_path, "-c", "from pip._internal.cli.main import main"],
                log_cmd_str="<checking pip's availability>",
                log_stdout=False,
                log_stderr=False,
            ).returncode
        )

    def _maintenance_lock(self) -> BaseFileLock:
        from filelock import FileLock  # ruff:ignore[import-outside-top-level]  # pulls in asyncio, slows startup

        self.root.parent.mkdir(parents=True, exist_ok=True)
        return FileLock(self.root.with_name(f".{self.root.name}.lock"))

    def _create(self, pip_args: list[str], *, verbose: bool, reinstall_pip: bool | None = None) -> None:
        if not self.is_valid:
            # Run the venv CLI, then print the pip wheel the base interpreter's ensurepip would install, checking the
            # distro wheel directory first as ensurepip does. Debian strips both locations, which prints an empty line.
            script: Final[str] = (
                "import sys, sysconfig, venv; from pathlib import Path; venv.main(sys.argv[1:]); "
                "wheel_dirs = [sysconfig.get_config_var('WHEEL_PKG_DIR'), "
                "Path(sysconfig.get_path('stdlib'), 'ensurepip', '_bundled')]; "
                "wheels = (str(wheel) for folder in wheel_dirs if folder "
                "for wheel in sorted(Path(folder).glob('pip-*.whl'), reverse=True)); "
                "print(next(wheels, ''))"
            )
            with animate("creating shared libraries", do_animation=not verbose):
                create_process = run_subprocess(
                    [get_default_python(), "-c", script, "--without-pip", "--clear", self.root], run_dir=str(self.root)
                )
            subprocess_post_check(create_process)
            self._is_valid = None

            should_reinstall_pip = not shared_libs_auto_upgrade_disabled() if reinstall_pip is None else reinstall_pip
            # Reinstall pip so OS-vendor patches cannot enter the shared environment. Importing pip straight from the
            # base interpreter's bundled wheel skips the ensurepip install that the reinstall would replace anyway; it
            # goes through PYTHONPATH and -m because pip on Windows refuses to replace itself when started by path.
            if should_reinstall_pip and (bundled_pip := create_process.stdout.strip()):
                try:
                    self._install_pip(
                        pip_args=[*pip_args, "--force-reinstall"], verbose=verbose, raises=True, pythonpath=bundled_pip
                    )
                except PipxError:
                    # keep a working pip so a later offline run can still use the shared venv
                    self._bootstrap_pip()
                    raise
                self._is_valid = True
            else:
                self._bootstrap_pip()
                if should_reinstall_pip:
                    self._upgrade(pip_args=[*pip_args, "--force-reinstall"], verbose=verbose, raises=True)
                else:
                    logger.info("Skipping the shared pip reinstall because maintenance is disabled")

            # Remove setuptools before the .pth file exposes shared libraries to apps. Python <3.12 ensurepip installs
            # a copy that fails under 3.12+ because the standard library no longer includes distutils.
            if any(self.root.glob("*/site-packages/setuptools")) or any(self.root.glob("*/*/site-packages/setuptools")):
                run_subprocess([self.python_path, "-m", "pip", "--no-input", "uninstall", "-y", "setuptools"])

    def _bootstrap_pip(self) -> None:
        subprocess_post_check(run_subprocess([self.python_path, "-m", "ensurepip", "--upgrade", "--default-pip"]))

    @property
    def is_valid(self) -> bool:
        with self._lock:
            if self._is_valid is None:
                self._is_valid = (
                    self.python_path.is_file()
                    and _venv_python_is_valid(self.python_path)
                    and self.pip_path.is_file()
                    and (self.site_packages[0] / "pip" / "_internal" / "cli" / "main.py").is_file()
                )
            return self._is_valid

    @property
    def needs_upgrade(self) -> bool:
        if self.has_been_updated_this_run:
            return False

        if not self.pip_path.is_file():
            return True

        now = time.time()
        time_since_last_update_sec = now - self.pip_path.stat().st_mtime
        if not self.has_been_logged_this_run:
            logger.info(
                "Time since last upgrade of shared libs, in seconds: %.0f. "
                "Upgrade will be run by pipx if greater than %.0f.",
                time_since_last_update_sec,
                SHARED_LIBS_MAX_AGE_SEC,
            )
            self.has_been_logged_this_run = True
        return time_since_last_update_sec > SHARED_LIBS_MAX_AGE_SEC

    def upgrade(self, *, pip_args: list[str], verbose: bool = False, raises: bool = False) -> None:
        with in_turn(lambda: self.has_been_updated_this_run), self._lock, self._maintenance_lock():
            self._upgrade(pip_args=pip_args, verbose=verbose, raises=raises)

    def _upgrade(self, *, pip_args: list[str], verbose: bool, raises: bool) -> None:
        if not self.is_valid:
            self._create(verbose=verbose, pip_args=pip_args, reinstall_pip=True)
            return

        if self.has_been_updated_this_run:
            logger.info("Already upgraded libraries in %s", self.root)
            return

        self._install_pip(pip_args=pip_args, verbose=verbose, raises=raises)

    def _install_pip(self, *, pip_args: list[str], verbose: bool, raises: bool, pythonpath: str | None = None) -> None:
        logger.info("Upgrading shared libraries in %s", self.root)

        filtered_pip_args = [arg for arg in pip_args if arg != "--editable"]
        if not verbose:
            filtered_pip_args.append("-q")

        try:
            with animate("upgrading shared libraries", do_animation=not verbose):
                upgrade_process = run_subprocess(
                    [
                        self.python_path,
                        "-m",
                        "pip",
                        "--no-input",
                        "--disable-pip-version-check",
                        "install",
                        "--upgrade",
                        *filtered_pip_args,
                        "pip >= 26.1",
                    ],
                    env_overrides={"PYTHONPATH": pythonpath},
                )
            subprocess_post_check(upgrade_process)

            self.has_been_updated_this_run = True
            self.pip_path.touch()

        except Exception:
            logger.exception("Failed to upgrade shared libraries", exc_info=not raises)
            if raises:
                raise


shared_libs = _SharedLibs()


__all__ = [
    "DISABLE_SHARED_LIBS_AUTO_UPGRADE",
    "SHARED_LIBS_MAX_AGE_SEC",
    "shared_libs",
    "shared_libs_auto_upgrade_disabled",
    "skip_shared_libs_maintenance",
]
