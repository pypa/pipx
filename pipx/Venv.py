#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from pathlib import Path
import pkgutil
from pipx.animate import animate
from pipx.constants import DEFAULT_PYTHON
from pipx.util import rmdir, WINDOWS, PipxError
import subprocess
from typing import List, Optional, Union, Sequence


GET_BINARIES_SCRIPT = pkgutil.get_data("pipx", "get_binaries.py").decode("utf-8")
GET_VERSION_SCRIPT = pkgutil.get_data("pipx", "get_version.py").decode("utf-8")
GET_PACKAGE_DEPS_SCRIPT = pkgutil.get_data(
    "pipx", "get_package_dependencies.py"
).decode("utf-8")


class Venv:
    """Abstraction for a virtual environment with various useful methods for pipx"""

    def __init__(
        self, path: Path, *, verbose: bool = False, python: str = DEFAULT_PYTHON
    ) -> None:
        self.root = path
        self._python = python
        self.bin_path = path / "bin" if not WINDOWS else path / "Scripts"
        self.python_path = self.bin_path / ("python" if not WINDOWS else "python.exe")
        self.verbose = verbose
        self.do_animation = not verbose

    def create_venv(self, venv_args: List[str], pip_args: List[str]) -> None:
        with animate("creating virtual environment", self.do_animation):
            _run([self._python, "-m", "venv"] + venv_args + [str(self.root)])
            ignored_args = ["--editable"]
            _pip_args = [arg for arg in pip_args if arg not in ignored_args]
            self.upgrade_package("pip", _pip_args)

    def remove_venv(self) -> None:
        rmdir(self.root)

    def install_package(self, package_or_url: str, pip_args: List[str]) -> None:
        with animate(f"installing package {package_or_url!r}", self.do_animation):
            if pip_args is None:
                pip_args = []
            cmd = ["install"] + pip_args + [package_or_url]
            self._run_pip(cmd)

    def get_package_dependencies(self, package: str) -> List[str]:
        return (
            subprocess.run(
                [str(self.python_path), "-c", GET_PACKAGE_DEPS_SCRIPT, package],
                stdout=subprocess.PIPE,
            )
            .stdout.decode()
            .split()
        )

    def get_python_version(self) -> str:
        return (
            subprocess.run([str(self.python_path), "--version"], stdout=subprocess.PIPE)
            .stdout.decode()
            .strip()
        )

    def get_package_version(self, package: str) -> Optional[str]:
        version = (
            subprocess.run(
                [str(self.python_path), "-c", GET_VERSION_SCRIPT, package],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            .stdout.decode()
            .strip()
        )
        if version:
            return version
        else:
            return None

    def get_package_binary_paths(self, package: str) -> List[Path]:
        if not Path(self.python_path).exists():
            return []
        binaries = (
            subprocess.run(
                [
                    str(self.python_path),
                    "-c",
                    GET_BINARIES_SCRIPT,
                    package,
                    self.bin_path,
                ],
                stdout=subprocess.PIPE,
            )
            .stdout.decode()
            .split()
        )

        binary_paths = {self.bin_path / b for b in binaries}
        if WINDOWS:
            for binary in binary_paths:
                # windows has additional files staring with the same name that are required
                # to run the binary
                for win_exec in binary.parent.glob(f"{binary.name}*"):
                    binary_paths.add(win_exec)

        valid_binary_paths = list(filter(lambda p: p.exists(), binary_paths))
        return valid_binary_paths

    def run_binary(self, binary: str, binary_args: List[str]):
        cmd = [str(self.bin_path / binary)] + binary_args
        try:
            return _run(cmd, check=False)
        except KeyboardInterrupt:
            pass

    def upgrade_package(self, package_or_url: str, pip_args: List[str]):
        self._run_pip(["install"] + pip_args + ["--upgrade", package_or_url])

    def _run_pip(self, cmd):
        cmd = [self.python_path, "-m", "pip"] + cmd
        if not self.verbose:
            cmd.append("-q")
        return _run(cmd)


def _run(cmd: Sequence[Union[str, Path]], check=True) -> int:
    """Run arbitrary command as subprocess"""

    cmd_str = " ".join(str(c) for c in cmd)
    logging.info(f"running {cmd_str}")
    # windows cannot take Path objects, only strings
    cmd_str_list = [str(c) for c in cmd]
    returncode = subprocess.run(cmd_str_list).returncode
    if check and returncode:
        raise PipxError(f"{cmd_str!r} failed")
    return returncode
