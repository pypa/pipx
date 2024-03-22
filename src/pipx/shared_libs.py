import datetime
import logging
import time
from pathlib import Path
from typing import List, Optional

from pipx import paths
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
        self.root = paths.ctx.shared_libs
        self.bin_path, self.python_path, self.man_path = get_venv_paths(self.root)
        self.pip_path = self.bin_path / ("pip" if not WINDOWS else "pip.exe")
        # i.e. bin_path is ~/.local/share/pipx/shared/bin
        # i.e. python_path is ~/.local/share/pipx/shared/python
        self._site_packages: Optional[Path] = None
        self.has_been_updated_this_run = False
        self.has_been_logged_this_run = False

    @property
    def site_packages(self) -> Path:
        if self._site_packages is None:
            self._site_packages = get_site_packages(self.python_path)

        return self._site_packages

    def create(self, pip_args: List[str], verbose: bool = False) -> None:
        if not self.is_valid:
            with animate("creating shared libraries", not verbose):
                create_process = run_subprocess(
                    [DEFAULT_PYTHON, "-m", "venv", "--clear", self.root], run_dir=str(self.root)
                )
            subprocess_post_check(create_process)
            # Recompute these paths, as they might resolve differently now, see comment in get_venv_paths
            self.bin_path, self.python_path, self.man_path = get_venv_paths(self.root)

            # ignore installed packages to ensure no unexpected patches from the OS vendor
            # are used
            pip_args = pip_args or []
            pip_args.append("--force-reinstall")
            self.upgrade(pip_args=pip_args, verbose=verbose)

    @property
    def is_valid(self) -> bool:
        if self.python_path.is_file():
            check_pip = "import importlib.util; print(importlib.util.find_spec('pip'))"
            out = run_subprocess(
                [self.python_path, "-c", check_pip],
                capture_stderr=False,
                log_cmd_str="<checking pip's availability>",
            ).stdout.strip()

            return self.pip_path.is_file() and out != "None"
        else:
            return False

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

    def upgrade(self, *, pip_args: List[str], verbose: bool = False) -> None:
        if not self.is_valid:
            self.create(verbose=verbose, pip_args=pip_args)
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
                        "--no-input",
                        "--disable-pip-version-check",
                        "install",
                        *_pip_args,
                        "--upgrade",
                        "pip >= 23.1",
                    ]
                )
            subprocess_post_check(upgrade_process)

            self.has_been_updated_this_run = True
            self.pip_path.touch()

        except Exception:
            logger.error("Failed to upgrade shared libraries", exc_info=True)


shared_libs = _SharedLibs()
