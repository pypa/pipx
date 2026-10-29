from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Self

if TYPE_CHECKING:
    from collections.abc import Sequence

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


__all__ = [
    "DEFAULT_BACKEND_OPTIONS",
    "DEFAULT_COOLDOWN_OPTIONS",
    "BackendOptions",
    "CooldownOptions",
    "ExposureOptions",
]
