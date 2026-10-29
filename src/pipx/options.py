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
    cli: str | None = None
    env: str | None = None


# no --backend and no PIPX_DEFAULT_BACKEND handed over: a Venv falls back to its record, then the environment
DEFAULT_BACKEND_OPTIONS: Final[BackendOptions] = BackendOptions()


# --cooldown and PIPX_COOLDOWN stay apart, so install can let a lock file override the machine-wide policy
@dataclass(frozen=True, slots=True, kw_only=True)
class CooldownOptions:
    cli_days: int | None = None
    env_days: int | None = None

    @property
    def days(self) -> int | None:
        return self.cli_days if self.cli_days is not None else self.env_days


DEFAULT_COOLDOWN_OPTIONS: Final[CooldownOptions] = CooldownOptions()


@dataclass(frozen=True, slots=True, kw_only=True)
class ExposureOptions:
    include_apps: bool = True
    include_dependencies: bool = False
    include_resources_from: Sequence[str] = ()
    suffix: str = ""

    @classmethod
    def recorded(cls, package_info: PackageInfo) -> Self:
        return cls(
            include_apps=package_info.include_apps,
            include_dependencies=package_info.include_dependencies,
            include_resources_from=package_info.include_resources_from,
            suffix=package_info.suffix,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class InstallOptions:
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
    cooldown: CooldownOptions = DEFAULT_COOLDOWN_OPTIONS
    pinned: bool | None = None
    preserve_existing: bool = False
    fetch_python: FetchPythonOptions = FetchPythonOptions.NEVER
    replace_expected_apps: bool = False
    replace_lock: bool = False
    emit_output: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class InjectOptions:
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
    local_bin_dir: Path
    local_man_dir: Path
    leave_deps: bool
    verbose: bool


# upgrade-all shares this record; skip applies to upgrade-all alone, install, python and venv_args to upgrade alone
@dataclass(frozen=True, slots=True, kw_only=True)
class UpgradeOptions:
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
    local_bin_dir: Path
    local_man_dir: Path
    python: str
    verbose: bool
    python_flag_passed: bool = False
    backend: BackendOptions = DEFAULT_BACKEND_OPTIONS
    skip: Sequence[str] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class SyncOptions:
    local_bin_dir: Path
    local_man_dir: Path
    python: str
    verbose: bool
    prune: bool
    backend: BackendOptions


@dataclass(frozen=True, slots=True, kw_only=True)
class ListOptions:
    include_injected: bool
    json_format: bool
    short_format: bool
    pinned_only: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class OutdatedOptions:
    include_injected: bool
    upgradable_only: bool = False
    pip_args: Sequence[str] = ()
    skip: Collection[str] = ()
    backend: BackendOptions = DEFAULT_BACKEND_OPTIONS


@dataclass(frozen=True, slots=True, kw_only=True)
class RunOptions:
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
    "DEFAULT_COOLDOWN_OPTIONS",
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
