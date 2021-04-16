import datetime
import logging
import time
from pathlib import Path
from typing import List, Optional

from pipx import constants
from pipx.animate import animate
from pipx.constants import WINDOWS
from pipx.interpreter import DEFAULT_PYTHON
from pipx.util import (
    get_site_packages,
    get_venv_paths,
    run_subprocess,
    subprocess_post_check,
)

logger = logging.getLogger(__name__)


SHARED_LIBS_MAX_AGE_SEC = datetime.timedelta(days=30).total_seconds()


class _SharedLibs:
    def __init__(self) -> None:
        self.root = constants.PIPX_SHARED_LIBS
        self.bin_path, self.python_path = get_venv_paths(self.root)
        self.pip_path = self.bin_path / ("pip" if not WINDOWS else "pip.exe")
        # i.e. bin_path is ~/.local/pipx/shared/bin
        # i.e. python_path is ~/.local/pipx/shared/python
        self._site_packages: Optional[Path] = None
        self.has_been_updated_this_run = False
        self.has_been_logged_this_run = False

    @property
    def site_packages(self) -> Path:
        if self._site_packages is None:
            self._site_packages = get_site_packages(self.python_path)

        return self._site_packages

    def create(self, verbose: bool = False) -> None:
        if not self.is_valid:
            with animate("creating shared libraries", not verbose):
                create_process = run_subprocess(
                    [DEFAULT_PYTHON, "-m", "venv", "--clear", self.root]
                )
            subprocess_post_check(create_process)

            # ignore installed packages to ensure no unexpected patches from the OS vendor
            # are used
            self.upgrade(pip_args=["--force-reinstall"], verbose=verbose)

    @property
    def is_valid(self) -> bool:
        return self.python_path.is_file() and self.pip_path.is_file()

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
                f"Time since last upgrade of shared libs, in seconds: {time_since_last_update_sec:.0f}. "
                f"Upgrade will be run by pipx if greater than {SHARED_LIBS_MAX_AGE_SEC:.0f}."
            )
            self.has_been_logged_this_run = True
        return time_since_last_update_sec > SHARED_LIBS_MAX_AGE_SEC

    def upgrade(
        self, *, pip_args: Optional[List[str]] = None, verbose: bool = False
    ) -> None:
        if not self.is_valid:
            self.create(verbose=verbose)
            return

        # Don't try to upgrade multiple times per run
        if self.has_been_updated_this_run:
            logger.info(f"Already upgraded libraries in {self.root}")
            return

        if pip_args is None:
            pip_args = []

        logger.info(f"Upgrading shared libraries in {self.root}")

        ignored_args = ["--editable"]
        _pip_args = [arg for arg in pip_args if arg not in ignored_args]
        if not verbose:
            _pip_args.append("-q")
        try:
            with animate("upgrading shared libraries", not verbose):
                upgrade_process = run_subprocess(
                    [
                        self.python_path,
                        "-m",
                        "pip",
                        "--disable-pip-version-check",
                        "install",
                        *_pip_args,
                        "--upgrade",
                        "pip",
                        "setuptools",
                        "wheel",
                    ]
                )
            subprocess_post_check(upgrade_process)

            self.has_been_updated_this_run = True
            self.pip_path.touch()

        except Exception:
            logger.error("Failed to upgrade shared libraries", exc_info=True)


shared_libs = _SharedLibs()
