import datetime
import logging
import time
from configparser import ConfigParser
from contextlib import suppress
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet

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

    try:
        config = ConfigParser()
        with open(pyvenv_cfg, encoding="utf-8") as f:
            # ConfigParser needs a section header, pyvenv.cfg doesn't have one
            config.read_string("[DEFAULT]\n" + f.read())
        home = config.get("DEFAULT", "home", fallback=None)
        if home:
            # The home path points to the directory containing the original python.exe
            original_python = Path(home) / "python.exe"
            if not original_python.is_file():
                logger.info(f"Shared libs venv references a missing Python interpreter: {original_python}")
                return False
    except Exception:
        # If we can't read pyvenv.cfg, assume the venv is valid
        pass

    return True


class _SharedLibs:
    def __init__(self) -> None:
        self._site_packages: dict[Path, Path] = {}
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
    def site_packages(self) -> Path:
        if self.python_path not in self._site_packages:
            self._site_packages[self.python_path] = get_site_packages(self.python_path)

        return self._site_packages[self.python_path]

    def create(self, pip_args: list[str], verbose: bool = False) -> None:
        if not self.is_valid:
            with animate("creating shared libraries", not verbose):
                create_process = run_subprocess(
                    [DEFAULT_PYTHON, "-m", "venv", "--clear", self.root], run_dir=str(self.root)
                )
            subprocess_post_check(create_process)

            # ignore installed packages to ensure no unexpected patches from the OS vendor
            # are used
            pip_args = pip_args or []
            pip_args.append("--force-reinstall")
            self.upgrade(pip_args=pip_args, verbose=verbose, raises=True)

    @property
    def is_valid(self) -> bool:
        if self.python_path.is_file():
            # On Windows, check that the venv's underlying Python still exists
            if not _venv_python_is_valid(self.python_path):
                return False

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

    def upgrade(self, *, pip_args: list[str], verbose: bool = False, raises: bool = False) -> None:
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

        user_pip_req = None
        for arg in _pip_args:
            with suppress(InvalidRequirement):
                if (req := Requirement(arg)).name == "pip":
                    user_pip_req = req
                    break

        add_default = not user_pip_req or not (user_pip_req.specifier & SpecifierSet(">=23.1"))
        install_args = [*_pip_args, "pip >= 23.1"] if add_default else _pip_args

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
                        "--upgrade",
                        *install_args,
                    ]
                )
            subprocess_post_check(upgrade_process)

            self.has_been_updated_this_run = True
            self.pip_path.touch()

        except Exception:
            logger.error("Failed to upgrade shared libraries", exc_info=not raises)
            if raises:
                raise


shared_libs = _SharedLibs()
