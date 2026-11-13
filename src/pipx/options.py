from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from pipx.constants import FetchPythonOptions

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class BackendOptions:
    """Backend chosen on the command line and in the environment.

    :param cli: the backend named by ``--backend``, or None.
    :param env: the backend named by ``PIPX_DEFAULT_BACKEND``, or None.
    """

    cli: str | None = None
    env: str | None = None


# no --backend and no PIPX_DEFAULT_BACKEND handed over: a Venv falls back to its record, then the environment
#: Backend options with nothing chosen.
DEFAULT_BACKEND_OPTIONS: Final[BackendOptions] = BackendOptions()


# --cooldown and PIPX_COOLDOWN stay apart, so install can let a lock file override the machine-wide policy
@dataclass(frozen=True, slots=True, kw_only=True)
class CooldownOptions:
    """Cooldown in days, chosen on the command line and in the environment.

    :param cli_days: the cooldown given by ``--cooldown``, or None.
    :param env_days: the cooldown given by ``PIPX_COOLDOWN``, or None.
    """

    cli_days: int | None = None
    env_days: int | None = None

    @property
    def days(self) -> int | None:
        """Return the cooldown in days, the command line value first.

        The result is None when neither value is set.
        """
        return self.cli_days if self.cli_days is not None else self.env_days


#: the cooldown options a command uses when none are given.
DEFAULT_COOLDOWN_OPTIONS: Final[CooldownOptions] = CooldownOptions()


@dataclass(frozen=True, slots=True, kw_only=True)
class ExposureOptions:
    """Options that choose which apps and dependencies an environment exposes.

    :param include_apps: whether to expose the apps of the environment.
    :param include_dependencies: whether to expose the apps of its dependencies.
    :param include_resources_from: packages whose shared resources are exposed as well.
    :param suffix: the suffix appended to every exposed app name.
    """

    include_apps: bool = True
    include_dependencies: bool = False
    include_resources_from: Sequence[str] = field(default_factory=list)
    suffix: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class EnvironmentOptions:
    """Options that choose how the install builds a new environment.

    :param python: the Python interpreter to build the environment with, or None for the default.
    :param venv_args: extra arguments passed when creating the environment.
    :param python_flag_passed: whether ``--python`` was given on the command line.
    :param fetch_python: whether to fetch a missing Python interpreter.
    :param preinstall_packages: packages installed before the main package, or None.
    """

    python: str | None
    venv_args: list[str]
    python_flag_passed: bool = False
    fetch_python: FetchPythonOptions = FetchPythonOptions.NEVER
    preinstall_packages: list[str] | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ExistingOptions:
    """Options that choose what the install does with an environment that already exists.

    :param force: whether to replace an existing environment.
    :param reinstall: whether the install rebuilds an existing environment.
    :param preserve: whether to keep an existing environment that fails to install.
    :param upgrade: whether to upgrade the installed package.
    :param upgrade_strategy: the pip upgrade strategy, or None.
    """

    force: bool
    reinstall: bool = False
    preserve: bool = False
    upgrade: bool = False
    upgrade_strategy: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class RecordOptions:
    """Options that override what an existing environment recorded.

    :param expected_apps: apps the install must expose.
    :param replace_expected_apps: whether the expected apps replace the recorded ones.
    :param lock_file: the lock file to install from, or None.
    :param replace_lock: whether to replace the lock file.
    :param exposure_enabled: whether exposure is enabled, or None to keep the recorded state.
    :param pinned: whether the environment is pinned, or None to keep the recorded state.
    """

    expected_apps: Sequence[str] = ()
    replace_expected_apps: bool = False
    lock_file: Path | None = None
    replace_lock: bool = False
    exposure_enabled: bool | None = None
    pinned: bool | None = None


#: the record options of an install that keeps everything the environment recorded.
DEFAULT_RECORD_OPTIONS: Final[RecordOptions] = RecordOptions()


@dataclass(frozen=True, slots=True, kw_only=True)
class InstallOptions:
    """Options of the install command.

    :param local_bin_dir: the directory the app links are placed in.
    :param local_man_dir: the directory the man pages are placed in.
    :param environment: how a new environment is built.
    :param existing: what happens to an environment that already exists.
    :param pip_args: extra arguments passed to pip.
    :param verbose: whether to print verbose output.
    :param backend: the backend that installs the package.
    :param exposure: which apps and dependencies are exposed.
    :param record: what overrides the state the environment recorded.
    :param cooldown: the cooldown applied to the new releases.
    :param emit_output: whether to emit output messages.
    """

    local_bin_dir: Path
    local_man_dir: Path
    environment: EnvironmentOptions
    existing: ExistingOptions
    pip_args: list[str]
    verbose: bool
    backend: BackendOptions
    exposure: ExposureOptions = ExposureOptions()
    record: RecordOptions = DEFAULT_RECORD_OPTIONS
    cooldown: CooldownOptions = DEFAULT_COOLDOWN_OPTIONS
    emit_output: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class InjectOptions:
    """Options of the inject command.

    :param pip_args: extra arguments passed to pip.
    :param verbose: whether to print verbose output.
    :param include_apps: whether to expose the apps of the injected package.
    :param include_dependencies: whether to expose the apps of its dependencies.
    :param include_resources_from: packages whose shared resources are exposed as well.
    :param force: whether to inject even when the package is already present.
    :param force_reinstall: whether an injected package is reinstalled.
    :param with_suffix: whether the exposed app names carry the environment suffix.

    :param backend: the backend that installs the package.
    :param cooldown_days: the cooldown in days applied to the new releases, or None.
    :param pinned: whether the environment is pinned, or None to keep the recorded state.
    :param emit_output: whether to emit output messages.
    """

    pip_args: list[str]
    verbose: bool
    include_apps: bool
    include_dependencies: bool
    include_resources_from: Sequence[str]
    force: bool
    force_reinstall: bool = True
    with_suffix: bool
    backend: BackendOptions = DEFAULT_BACKEND_OPTIONS
    cooldown_days: int | None
    pinned: bool | None = None
    emit_output: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class UninjectOptions:
    """Options of the uninject command.

    :param local_bin_dir: the directory the app links are placed in.
    :param local_man_dir: the directory the man pages are placed in.
    :param leave_deps: whether the dependencies of the injected package are kept.
    :param verbose: whether to print verbose output.
    """

    local_bin_dir: Path
    local_man_dir: Path
    leave_deps: bool
    verbose: bool


# upgrade-all shares this record; skip applies to upgrade-all alone, install, python and venv_args to upgrade alone
@dataclass(frozen=True, slots=True, kw_only=True)
class UpgradeOptions:
    """Options of the upgrade command.

    :param pip_args: extra arguments passed to pip.
    :param verbose: whether to print verbose output.
    :param include_injected: whether the injected packages are upgraded too.
    :param force: whether to upgrade even when the package is up to date.
    :param python_flag_passed: whether ``--python`` was given on the command line.

    :param backend: the backend that upgrades the package.
    :param cooldown: the cooldown applied to the new releases.
    :param install: whether to install the package when it is missing.
    :param python: the Python interpreter to upgrade with, or None for the default.
    :param venv_args: extra arguments passed when creating the environment.
    :param skip: the packages to leave out of the upgrade.
    """

    pip_args: list[str]
    verbose: bool
    include_injected: bool
    force: bool
    python_flag_passed: bool
    backend: BackendOptions
    cooldown: CooldownOptions
    install: bool = False
    python: str | None = None
    venv_args: list[str] = field(default_factory=list)
    skip: Sequence[str] = ()


# reinstall-all, repair and the interpreter upgrade rebuild through reinstall; skip applies to reinstall-all alone
@dataclass(frozen=True, slots=True, kw_only=True)
class ReinstallOptions:
    """Options of the reinstall command.

    :param local_bin_dir: the directory the app links are placed in.
    :param local_man_dir: the directory the man pages are placed in.
    :param python: the Python interpreter to rebuild the environment with.
    :param verbose: whether to print verbose output.
    :param python_flag_passed: whether ``--python`` was given on the command line.
    :param backend: the backend that installs the package.
    :param skip: the packages to leave out of the reinstall.
    """

    local_bin_dir: Path
    local_man_dir: Path
    python: str
    verbose: bool
    python_flag_passed: bool = False
    backend: BackendOptions = DEFAULT_BACKEND_OPTIONS
    skip: Sequence[str] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class SyncOptions:
    """Options of the manifest sync command.

    :param local_bin_dir: the directory the app links are placed in.
    :param local_man_dir: the directory the man pages are placed in.
    :param python: the Python interpreter to build the environments with.
    :param verbose: whether to print verbose output.
    :param prune: whether environments missing from the manifest are removed.
    :param backend: the backend that installs the packages.
    """

    local_bin_dir: Path
    local_man_dir: Path
    python: str
    verbose: bool
    prune: bool
    backend: BackendOptions


@dataclass(frozen=True, slots=True, kw_only=True)
class ListOptions:
    """Options of the list command.

    :param include_injected: whether the injected packages are listed too.
    :param json_format: whether to print the list as JSON.
    :param short_format: whether to print only the package names.
    :param pinned_only: whether to list only the pinned packages.
    """

    include_injected: bool
    json_format: bool
    short_format: bool
    pinned_only: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class OutdatedOptions:
    """Options of the outdated command.

    :param include_injected: whether the injected packages are checked too.
    :param upgradable_only: whether to report only the packages that can be upgraded.
    :param pip_args: extra arguments passed to pip.
    :param skip: the packages to leave out of the check.
    :param backend: the backend that looks up the newest versions.
    """

    include_injected: bool
    upgradable_only: bool = False
    pip_args: Sequence[str] = ()
    skip: Collection[str] = ()
    backend: BackendOptions = DEFAULT_BACKEND_OPTIONS


@dataclass(frozen=True, slots=True, kw_only=True)
class RunInterpreterOptions:
    """Options that choose the Python interpreter the run command starts.

    :param python: the Python interpreter to run with.
    :param python_args: extra arguments passed to the Python interpreter.
    :param python_flag_passed: whether ``--python`` was given on the command line.
    :param fetch_python: whether to fetch a missing Python interpreter.
    """

    python: str
    python_args: list[str]
    python_flag_passed: bool
    fetch_python: FetchPythonOptions


@dataclass(frozen=True, slots=True, kw_only=True)
class AppLookupOptions:
    """Options that choose how the run command finds the app.

    :param is_path: whether the app is given as a path rather than a package name.
    :param pypackages: whether to use a ``__pypackages__`` directory.
    :param no_path_check: whether to skip the check that the app is not on the PATH.
    """

    is_path: bool
    pypackages: bool
    no_path_check: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class RunOptions:
    """Options of the run command.

    :param app_args: arguments passed to the app.
    :param dependencies: extra requirements the environment is built with.
    :param interpreter: the Python interpreter to run with.
    :param lookup: how the app is found.
    :param pip_args: extra arguments passed to pip.
    :param venv_args: extra arguments passed when creating the environment.
    :param verbose: whether to print verbose output.
    :param use_cache: whether to reuse a cached environment.
    :param refresh: whether to rebuild the cached environment.
    :param backend: the backend that installs the package.
    :param cooldown: the cooldown applied to the new releases.
    """

    app_args: list[str]
    dependencies: list[str]
    interpreter: RunInterpreterOptions
    lookup: AppLookupOptions
    pip_args: list[str]
    venv_args: list[str]
    verbose: bool
    use_cache: bool
    refresh: bool
    backend: BackendOptions
    cooldown: CooldownOptions


__all__ = [
    "DEFAULT_BACKEND_OPTIONS",
    "DEFAULT_COOLDOWN_OPTIONS",
    "DEFAULT_RECORD_OPTIONS",
    "AppLookupOptions",
    "BackendOptions",
    "CooldownOptions",
    "EnvironmentOptions",
    "ExistingOptions",
    "ExposureOptions",
    "InjectOptions",
    "InstallOptions",
    "ListOptions",
    "OutdatedOptions",
    "RecordOptions",
    "ReinstallOptions",
    "RunInterpreterOptions",
    "RunOptions",
    "SyncOptions",
    "UninjectOptions",
    "UpgradeOptions",
]
