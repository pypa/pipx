import logging
from pathlib import Path
from typing import List

from pipx.animate import animate
from pipx.constants import DEFAULT_PYTHON, PIPX_SHARED_LIBS, WINDOWS
from pipx.util import get_venv_paths, get_site_packages, run


class _SharedLibs:
    def __init__(self):
        self.root = PIPX_SHARED_LIBS
        self.bin_path, self.python_path = get_venv_paths(self.root)
        # i.e. bin_path is ~/.local/pipx/shared/bin
        # i.e. python_path is ~/.local/pipx/shared/python
        self._site_packages = None
        self.has_been_updated_this_run = False

    @property
    def site_packages(self) -> Path:
        if self._site_packages is None:
            self._site_packages = get_site_packages(self.python_path)

        return self._site_packages

    def create(self, pip_args: List[str], verbose: bool = False):
        if not self.is_valid:
            with animate("creating shared libraries", not verbose):
                run([DEFAULT_PYTHON, "-m", "venv", self.root])
            self.upgrade(pip_args, verbose)

    @property
    def is_valid(self):
        return (
            self.python_path.is_file()
            and (self.bin_path / ("pip" if not WINDOWS else "pip.exe")).is_file()
        )

    def upgrade(self, pip_args: List[str], verbose: bool = False):
        # Don't try to upgrade multiple times per run
        if self.has_been_updated_this_run:
            logging.info("Already upgraded libraries in", self.root)
            return
        logging.info("Upgrading shared libraries in", self.root)

        ignored_args = ["--editable"]
        _pip_args = [arg for arg in pip_args if arg not in ignored_args]
        if not verbose:
            _pip_args.append("-q")
        try:
            with animate("upgrading shared libraries", not verbose):
                run(
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
                self.has_been_updated_this_run = True
        except Exception:
            logging.error("Failed to upgrade shared libraries", exc_info=True)


shared_libs = _SharedLibs()
