from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final, Self

from pipx.constants import FetchPythonOptions

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from pathlib import Path

    from pipx.pipx_metadata_file import PackageInfo


@dataclass(frozen=True, slots=True, kw_only=True)
class BackendOptions:
    """Backend chosen on the command line and in the environment."""

    cli: str | None = None
    env: str | None = None


# no --backend and no PIPX_DEFAULT_BACKEND handed over: a Venv falls back to its record, then the environment
#: Backend options with nothing chosen.
DEFAULT_BACKEND_OPTIONS: Final[BackendOptions] = BackendOptions()


# --cooldown and PIPX_COOLDOWN stay apart, so install can let a lock file override the machine-wide policy
@dataclass(frozen=True, slots=True, kw_only=True)
class CooldownOptions:
    """Cooldown in days, chosen on the command line and in the environment."""

    cli_days: int | None = None
    env_days: int | None = None

    @property
    def days(self) -> int | None:
        """Return the cooldown in days, the command line value first.

        :returns: the number of days, or None when no cooldown is set.
        """
        return self.cli_days if self.cli_days is not None else self.env_days


_DEFAULT_COOLDOWN_OPTIONS: Final[CooldownOptions] = CooldownOptions()


@dataclass(frozen=True, slots=True, kw_only=True)
class ExposureOptions:
    """Options that choose which apps and dependencies an environment exposes."""

    include_apps: bool = True
    include_dependencies: bool = False
    include_resources_from: Sequence[str] = ()
    suffix: str = ""

    @classmethod
    def recorded(cls, package_info: PackageInfo) -> Self:
        """Return the exposure options that an environment was installed with.

        :param package_info: the package whose recorded options are read.
        :returns: the exposure options.
        """
        return cls(
            include_apps=package_info.include_apps,
            include_dependencies=package_info.include_dependencies,
            include_resources_from=package_info.include_resources_from,
            suffix=package_info.suffix,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class InstallOptions:
    """Options of the install command."""

    local_bin_dir: Path
    local_man_dir: Path
    python: str | None
    pip_args: list[str]
    venv_args: list[str]
    verbose: bool
    force: bool
    backend: BackendOptions
    reinstall: bool = False
    exposure: ExposureOptions = ExposureOptions()
    preinstall_packages: list[str] | None = None
    expected_apps: Sequence[str] = ()
    lock_file: Path | None = None
    python_flag_passed: bool = False
    exposure_enabled: bool | None = None
    upgrade: bool = False
    upgrade_strategy: str | None = None
    cooldown: CooldownOptions = _DEFAULT_COOLDOWN_OPTIONS
    pinned: bool | None = None
    preserve_existing: bool = False
    fetch_python: FetchPythonOptions = FetchPythonOptions.NEVER
    replace_expected_apps: bool = False
    replace_lock: bool = False
    emit_output: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class InjectOptions:
    """Options of the inject command."""

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
    """Options of the uninject command."""

    local_bin_dir: Path
    local_man_dir: Path
    leave_deps: bool
    verbose: bool


# upgrade-all shares this record; skip applies to upgrade-all alone, install, python and venv_args to upgrade alone
@dataclass(frozen=True, slots=True, kw_only=True)
class UpgradeOptions:
    """Options of the upgrade command."""

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
    """Options of the reinstall command."""

    local_bin_dir: Path
    local_man_dir: Path
    python: str
    verbose: bool
    python_flag_passed: bool = False
    backend: BackendOptions = DEFAULT_BACKEND_OPTIONS
    skip: Sequence[str] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class SyncOptions:
    """Options of the manifest sync command."""

    local_bin_dir: Path
    local_man_dir: Path
    python: str
    verbose: bool
    prune: bool
    backend: BackendOptions


@dataclass(frozen=True, slots=True, kw_only=True)
class ListOptions:
    """Options of the list command."""

    include_injected: bool
    json_format: bool
    short_format: bool
    pinned_only: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class OutdatedOptions:
    """Options of the outdated command."""

    include_injected: bool
    upgradable_only: bool = False
    pip_args: Sequence[str] = ()
    skip: Collection[str] = ()
    backend: BackendOptions = DEFAULT_BACKEND_OPTIONS


@dataclass(frozen=True, slots=True, kw_only=True)
class RunOptions:
    """Options of the run command."""

    app_args: list[str]
    dependencies: list[str]
    python: str
    pip_args: list[str]
    venv_args: list[str]
    is_path: bool
    pypackages: bool
    verbose: bool
    use_cache: bool
    python_args: list[str]
    refresh: bool
    no_path_check: bool
    backend: BackendOptions
    cooldown: CooldownOptions
    python_flag_passed: bool
    fetch_python: FetchPythonOptions


__all__ = [
    "DEFAULT_BACKEND_OPTIONS",
    "BackendOptions",
    "CooldownOptions",
    "ExposureOptions",
    "InjectOptions",
    "InstallOptions",
    "ListOptions",
    "OutdatedOptions",
    "ReinstallOptions",
    "RunOptions",
    "SyncOptions",
    "UninjectOptions",
    "UpgradeOptions",
]
