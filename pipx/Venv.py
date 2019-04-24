#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import pkgutil
import subprocess
from pathlib import Path
from typing import Dict, List, NamedTuple, Sequence, Union

from pipx.animate import animate
from pipx.constants import DEFAULT_PYTHON
from pipx.util import WINDOWS, PipxError, rmdir


class PipxVenvMetadata(NamedTuple):
    binaries: List[str]
    binary_paths: List[Path]
    binaries_of_dependencies: List[str]
    binary_paths_of_dependencies: Dict[str, List[Path]]
    package_version: str
    python_version: str


venv_metadata_inspector_raw = pkgutil.get_data("pipx", "venv_metadata_inspector.py")
assert venv_metadata_inspector_raw is not None, (
    "pipx could not find required file venv_metadata_inspector.py. "
    "Please report this error at https://github.com/pipxproject/pipx. Exiting."
)
VENV_METADATA_INSPECTOR = venv_metadata_inspector_raw.decode("utf-8")


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
        self._was_created_this_session = False

    def create_venv(self, venv_args: List[str], pip_args: List[str]) -> None:
        self._was_created_this_session = True
        with animate("creating virtual environment", self.do_animation):
            _run([self._python, "-m", "venv"] + venv_args + [str(self.root)])
            ignored_args = ["--editable"]
            _pip_args = [arg for arg in pip_args if arg not in ignored_args]
            self.upgrade_package("pip", _pip_args)

    def safe_to_remove(self) -> bool:
        return self._was_created_this_session

    def remove_venv(self) -> None:
        if self.safe_to_remove():
            rmdir(self.root)
        else:
            logging.warning(
                f"Not removing existing venv {self.root} because "
                "it was not created in this session"
            )

    def install_package(self, package_or_url: str, pip_args: List[str]) -> None:
        with animate(f"installing package {package_or_url!r}", self.do_animation):
            if pip_args is None:
                pip_args = []
            cmd = ["install"] + pip_args + [package_or_url]
            self._run_pip(cmd)

    def get_venv_metadata_for_package(self, package: str) -> PipxVenvMetadata:

        data = json.loads(
            subprocess.run(
                [
                    str(self.python_path),
                    "-c",
                    VENV_METADATA_INSPECTOR,
                    package,
                    str(self.bin_path),
                ],
                stdout=subprocess.PIPE,
            ).stdout.decode(),
            encoding="utf-8",
        )
        data["binary_paths"] = [Path(p) for p in data["binary_paths"]]

        data["binaries_of_dependencies"] = []
        for dep, raw_paths in data["binary_paths_of_dependencies"].items():
            paths = [Path(raw_path) for raw_path in raw_paths]
            data["binary_paths_of_dependencies"][dep] = paths
            data["binaries_of_dependencies"] += [path.name for path in paths]

        if WINDOWS:
            windows_bin_paths = set()
            for binary in data["binary_paths"]:
                # windows has additional files staring with the same name that are required
                # to run the binary
                for win_exec in binary.parent.glob(f"{binary.name}*"):
                    windows_bin_paths.add(win_exec)
            data["binary_paths"] = list(windows_bin_paths)
        return PipxVenvMetadata(**data)

    def get_python_version(self) -> str:
        return (
            subprocess.run([str(self.python_path), "--version"], stdout=subprocess.PIPE)
            .stdout.decode()
            .strip()
        )

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
