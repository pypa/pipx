from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path
    from subprocess import CompletedProcess


PIP: Final[str] = "pip"
UV: Final[str] = "uv"
KNOWN_BACKENDS: Final[tuple[str, ...]] = (PIP, UV)


class Backend(ABC):
    name: str

    @abstractmethod
    def create_venv(
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
    def install(
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
    ) -> CompletedProcess[str]: ...

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
    def run_raw_pip(
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


__all__ = [
    "KNOWN_BACKENDS",
    "PIP",
    "UV",
    "Backend",
]
