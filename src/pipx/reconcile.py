from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import TYPE_CHECKING

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from pipx.package_specifier import package_spec_satisfied
from pipx.result import OperationData

if TYPE_CHECKING:
    from pathlib import Path


def plan_tool_request(request: ToolRequest, state: ToolState | None) -> ReconcilePlan:
    if state is None:
        return ReconcilePlan(ReconcileAction.INSTALL)

    reasons: list[ReinstallReason] = []
    if canonicalize_name(request.package_name) != canonicalize_name(state.package_name) or _package_shape_changed(
        request, state
    ):
        reasons.append(ReinstallReason.PACKAGE_SPEC)
    if state.source_interpreter is None or request.python.resolve() != state.source_interpreter.resolve():
        reasons.append(ReinstallReason.PYTHON)
    if request.backend != state.backend:
        reasons.append(ReinstallReason.BACKEND)
    if request.pip_args != state.pip_args:
        reasons.append(ReinstallReason.PIP_ARGS)
    if request.venv_args != state.venv_args:
        reasons.append(ReinstallReason.VENV_ARGS)
    if request.include_dependencies != state.include_dependencies:
        reasons.append(ReinstallReason.INCLUDE_DEPENDENCIES)
    if reasons:
        return ReconcilePlan(ReconcileAction.REINSTALL, tuple(reasons))
    if _fixed_version_satisfied(request, state):
        return ReconcilePlan(ReconcileAction.NOOP)
    return ReconcilePlan(ReconcileAction.UPGRADE)


def _package_shape_changed(request: ToolRequest, state: ToolState) -> bool:
    try:
        requirement = Requirement(request.package_spec)
        installed_requirement = Requirement(state.package_spec)
    except InvalidRequirement:
        return request.package_spec != state.package_spec
    return (
        canonicalize_name(requirement.name) != canonicalize_name(installed_requirement.name)
        or requirement.extras != installed_requirement.extras
        or requirement.url != installed_requirement.url
    )


def _fixed_version_satisfied(request: ToolRequest, state: ToolState) -> bool:
    try:
        requirement = Requirement(request.package_spec)
    except InvalidRequirement:
        return False
    specifiers = list(requirement.specifier)
    return (
        len(specifiers) == 1
        and specifiers[0].operator in ("==", "===")
        and "*" not in specifiers[0].version
        and package_spec_satisfied(
            request.package_spec,
            state.package_name,
            state.version,
            state.package_spec,
        )
    )


class ReconcileAction(str, enum.Enum):
    INSTALL = "install"
    NOOP = "noop"
    REINSTALL = "reinstall"
    UPGRADE = "upgrade"


class ReinstallReason(str, enum.Enum):
    BACKEND = "backend"
    INCLUDE_DEPENDENCIES = "include-dependencies"
    PACKAGE_SPEC = "package-spec"
    PIP_ARGS = "pip-args"
    PYTHON = "python"
    VENV_ARGS = "venv-args"


@dataclass(frozen=True)
class ToolRequest:
    package_name: str
    package_spec: str
    python: Path
    backend: str
    pip_args: tuple[str, ...]
    venv_args: tuple[str, ...]
    include_dependencies: bool


@dataclass(frozen=True)
class ToolState:
    package_name: str
    package_spec: str
    version: str
    source_interpreter: Path | None
    backend: str
    pip_args: tuple[str, ...]
    venv_args: tuple[str, ...]
    include_dependencies: bool
    pinned: bool


@dataclass(frozen=True)
class ReconcilePlan(OperationData):
    action: ReconcileAction
    reasons: tuple[ReinstallReason, ...] = ()


__all__ = [
    "ReconcileAction",
    "ReconcilePlan",
    "ReinstallReason",
    "ToolRequest",
    "ToolState",
    "plan_tool_request",
]
