from __future__ import annotations

__lazy_modules__ = ["json", "pipx.util"]

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, TypedDict, cast

from pipx.util import PipxError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path
    from subprocess import CompletedProcess


#: Backend name for pip.
PIP: Final[str] = "pip"
#: Backend name for uv.
UV: Final[str] = "uv"
#: Names accepted by backend selection.
KNOWN_BACKENDS: Final[tuple[str, ...]] = (PIP, UV)


class Backend(ABC):
    """Installer contract shared by the pip and uv backends.

    :ivar name: the backend name written to environment metadata.
    """

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
    ) -> None:
        """Create an environment using the requested Python and installer options.

        :param root: path for the new environment.
        :param python: interpreter to use.
        :param venv_args: arguments for environment creation.
        :param pip_args: arguments for the installer.
        :param include_pip: install pip into the environment.
        :param verbose: show installer output.
        """

    def install_lock(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        lock_file: Path,
        pip_args: list[str],
        verbose: bool,
    ) -> CompletedProcess[str]:
        """Install the packages of a lock file into an environment.

        :param venv_root: the directory of the environment.
        :param venv_python: the interpreter of the environment.
        :param lock_file: the lock file to install from.
        :param pip_args: extra arguments for the installer.
        :param verbose: show the output of the installer.
        :returns: the completed installer process.
        """
        return self.install(
            venv_root=venv_root,
            venv_python=venv_python,
            requirements=["--requirement", str(lock_file)],
            pip_args=pip_args,
            verbose=verbose,
        )

    @abstractmethod
    def install(  # ruff:ignore[too-many-arguments]  # install flags map one-to-one onto backend CLI options
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        requirements: list[str],
        pip_args: list[str],
        no_deps: bool = False,
        upgrade_package: str | None = None,
        log_pip_errors: bool = True,
        verbose: bool,
    ) -> CompletedProcess[str]:
        """Install requirements into an environment.

        :param venv_root: path of the environment.
        :param venv_python: interpreter in the environment.
        :param requirements: packages or requirement files to install.
        :param pip_args: extra arguments for the installer.
        :param no_deps: skip dependencies.
        :param upgrade_package: package to upgrade, if any.
        :param log_pip_errors: write installer errors to the log.
        :param verbose: show installer output.
        :returns: the installer process result.
        """

    @staticmethod
    @abstractmethod
    def cooldown_args(cooldown_days: int | None) -> list[str]:
        """Return installer arguments that limit cache age.

        :param cooldown_days: maximum cache age, or None for no limit.
        :returns: installer arguments.
        """

    @abstractmethod
    def uninstall(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        packages: Sequence[str],
        verbose: bool,
    ) -> CompletedProcess[str]:
        """Uninstall packages from an environment.

        :param venv_root: path of the environment.
        :param venv_python: interpreter in the environment.
        :param packages: packages to uninstall.
        :param verbose: show installer output.
        :returns: the installer process result.
        """

    @abstractmethod
    def list_installed(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        not_required: bool,
    ) -> set[str]:
        """List packages installed in an environment.

        :param venv_root: path of the environment.
        :param venv_python: interpreter in the environment.
        :param not_required: include only packages without dependents.
        :returns: installed package names.
        """

    @abstractmethod
    def list_outdated(
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        index_args: list[str],
        exclude: list[str],
    ) -> tuple[OutdatedPackage, ...]:
        """List installed packages with newer available versions.

        :param venv_root: path of the environment.
        :param venv_python: interpreter in the environment.
        :param index_args: package index arguments.
        :param exclude: package names to omit.
        :returns: outdated packages.
        """

    @abstractmethod
    def run_raw_pip(  # ruff:ignore[too-many-arguments]  # passes raw pip invocation controls through
        self,
        *,
        venv_root: Path,
        venv_python: Path,
        args: list[str],
        capture_stdout: bool = True,
        capture_stderr: bool = True,
        verbose: bool,
        in_working_dir: bool = False,
    ) -> CompletedProcess[str]:
        """Run installer arguments directly in an environment.

        :param venv_root: path of the environment.
        :param venv_python: interpreter in the environment.
        :param args: installer arguments.
        :param capture_stdout: capture standard output.
        :param capture_stderr: capture standard error.
        :param verbose: show installer output.
        :param in_working_dir: run from the caller's working directory.
        :returns: the installer process result.
        """

    @abstractmethod
    def needs_shared_libs(self) -> bool:
        """Whether this backend uses pipx's shared package environment.

        :returns: whether shared libraries are needed.
        """

    @abstractmethod
    def upgrade_packaging_libraries(self, venv_python: Path, pip_args: list[str]) -> None:
        """Upgrade packaging tools in an environment.

        :param venv_python: interpreter in the environment.
        :param pip_args: extra installer arguments.
        """


def outdated_packages_from_process(process: CompletedProcess[str]) -> tuple[OutdatedPackage, ...]:
    if process.returncode:
        msg = f"Package backend exited with code {process.returncode}.\nstderr: {process.stderr}"
        raise PipxError(msg, wrap_message=False)
    try:
        return tuple(
            OutdatedPackage(name=entry["name"], version=entry["version"], latest_version=entry["latest_version"])
            for entry in cast("list[_OutdatedEntry]", json.loads(process.stdout))
        )
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        msg = "Package backend returned invalid JSON for an outdated query."
        raise PipxError(msg, wrap_message=False) from error


@dataclass(frozen=True, slots=True, kw_only=True)
class OutdatedPackage:
    """Installed package and the latest version known to its backend.

    :param name: package name.
    :param version: installed version.
    :param latest_version: newest known version.
    """

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
