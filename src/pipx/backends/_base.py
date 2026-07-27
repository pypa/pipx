from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, TypedDict, cast

from pipx.util import PipxError

if TYPE_CHECKING:
    from pathlib import Path
    from subprocess import CompletedProcess


PIP: Final[str] = "pip"
UV: Final[str] = "uv"
KNOWN_BACKENDS: Final[tuple[str, ...]] = (PIP, UV)


class Backend(ABC):
    name: str

    @abstractmethod
    def create_venv(  # ruff:ignore[too-many-arguments]  # backend contract mirrors the venv-creation CLI inputs
        self,
        root: Path,
        *,
        python: str,
        venv_args: list[str],
        pip_args: list[str],
        include_pip: bool,
        verbose: bool,
    ) -> None: ...

    @abstractmethod
    def install(  # ruff:ignore[too-many-arguments]  # install flags map one-to-one onto backend CLI options
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        requirements: list[str],
        pip_args: list[str],
        no_deps: bool = False,
        upgrade: bool = False,
        log_pip_errors: bool = True,
        verbose: bool = False,
        progress: bool = False,
    ) -> CompletedProcess[str]: ...

    def install_lock(  # ruff:ignore[too-many-arguments]  # forwards install inputs to install()
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        lock_file: Path,
        pip_args: list[str],
        verbose: bool = False,
        progress: bool = False,
    ) -> CompletedProcess[str]:
        return self.install(
            venv_root=venv_root,
            venv_python=venv_python,
            requirements=["--requirement", str(lock_file)],
            pip_args=pip_args,
            verbose=verbose,
            progress=progress,
        )

    @staticmethod
    @abstractmethod
    def cooldown_args(cooldown_days: int | None) -> list[str]: ...

    @abstractmethod
    def uninstall(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        package: str,
        verbose: bool,
    ) -> CompletedProcess[str]: ...

    @abstractmethod
    def list_installed(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        not_required: bool = False,
    ) -> set[str]: ...

    @abstractmethod
    def list_outdated(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        index_args: list[str],
    ) -> tuple[OutdatedPackage, ...]: ...

    @abstractmethod
    def run_raw_pip(  # ruff:ignore[too-many-arguments]  # passes raw pip invocation controls through
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        args: list[str],
        capture_stdout: bool = True,
        capture_stderr: bool = True,
        verbose: bool = False,
    ) -> CompletedProcess[str]: ...

    @abstractmethod
    def needs_shared_libs(self) -> bool: ...

    @abstractmethod
    def upgrade_packaging_libraries(
        self,
        venv_python: Path,
        pip_args: list[str],
        *,
        verbose: bool,
    ) -> None: ...


def outdated_packages_from_process(process: CompletedProcess[str]) -> tuple[OutdatedPackage, ...]:
    if process.returncode:
        msg = f"Package backend exited with code {process.returncode}.\nstderr: {process.stderr}"
        raise PipxError(
            msg,
            wrap_message=False,
        )
    return _parse_outdated_packages(process.stdout)


def _parse_outdated_packages(output: str) -> tuple[OutdatedPackage, ...]:
    try:
        return tuple(
            OutdatedPackage(entry["name"], entry["version"], entry["latest_version"])
            for entry in cast("list[_OutdatedEntry]", json.loads(output))
        )
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        msg = "Package backend returned invalid JSON for an outdated query."
        raise PipxError(msg, wrap_message=False) from error


@dataclass(frozen=True)
class OutdatedPackage:
    name: str
    version: str
    latest_version: str


class _OutdatedEntry(TypedDict):
    name: str
    version: str
    latest_version: str


__all__ = [
    "KNOWN_BACKENDS",
    "PIP",
    "UV",
    "Backend",
    "OutdatedPackage",
    "outdated_packages_from_process",
]
