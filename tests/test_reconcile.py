from dataclasses import replace
from pathlib import Path
from typing import Final

import pytest

from pipx.reconcile import (
    ReconcileAction,
    ReconcilePlan,
    ReinstallReason,
    ToolRequest,
    ToolState,
    plan_tool_request,
)

_REQUEST: Final[ToolRequest] = ToolRequest(
    package_name="example",
    package_spec="example==1.0",
    python=Path("/python"),
    backend="pip",
    pip_args=(),
    venv_args=(),
    include_dependencies=False,
)
_STATE: Final[ToolState] = ToolState(
    package_name="example",
    package_spec="example==1.0",
    version="1.0",
    source_interpreter=Path("/python"),
    backend="pip",
    pip_args=(),
    venv_args=(),
    include_dependencies=False,
    pinned=False,
)


def test_plan_tool_request_install() -> None:
    assert plan_tool_request(_REQUEST, None) == ReconcilePlan(ReconcileAction.INSTALL)


@pytest.mark.parametrize(
    "package_spec",
    [
        pytest.param("example", id="unconstrained"),
        pytest.param("example>=1", id="range"),
        pytest.param("example==1.*", id="wildcard"),
    ],
)
def test_plan_tool_request_mutable_spec_upgrades(package_spec: str) -> None:
    assert plan_tool_request(replace(_REQUEST, package_spec=package_spec), _STATE) == ReconcilePlan(
        ReconcileAction.UPGRADE
    )


def test_plan_tool_request_fixed_version_noop() -> None:
    assert plan_tool_request(_REQUEST, _STATE) == ReconcilePlan(ReconcileAction.NOOP)


def test_plan_tool_request_same_url_upgrades() -> None:
    package_spec = "example @ https://example.invalid/example.whl"
    assert plan_tool_request(
        replace(_REQUEST, package_spec=package_spec), replace(_STATE, package_spec=package_spec)
    ) == ReconcilePlan(ReconcileAction.UPGRADE)


@pytest.mark.parametrize(
    ("requested_spec", "installed_spec", "expected_plan"),
    [
        pytest.param("./example", "./example", ReconcilePlan(ReconcileAction.UPGRADE), id="same"),
        pytest.param(
            "./example",
            "./other",
            ReconcilePlan(ReconcileAction.REINSTALL, (ReinstallReason.PACKAGE_SPEC,)),
            id="changed",
        ),
    ],
)
def test_plan_tool_request_paths(
    requested_spec: str,
    installed_spec: str,
    expected_plan: ReconcilePlan,
) -> None:
    assert (
        plan_tool_request(
            replace(_REQUEST, package_spec=requested_spec),
            replace(_STATE, package_spec=installed_spec),
        )
        == expected_plan
    )


@pytest.mark.parametrize(
    "tool_state",
    [
        pytest.param(replace(_STATE, package_spec="example[feature]==1.0"), id="extras"),
        pytest.param(
            replace(_STATE, package_spec="example @ https://example.invalid/example.whl"),
            id="source",
        ),
        pytest.param(replace(_STATE, package_name="other"), id="package-name"),
    ],
)
def test_plan_tool_request_package_shape_reinstalls(tool_state: ToolState) -> None:
    assert plan_tool_request(_REQUEST, tool_state) == ReconcilePlan(
        ReconcileAction.REINSTALL,
        (ReinstallReason.PACKAGE_SPEC,),
    )


@pytest.mark.parametrize(
    ("tool_request", "reason"),
    [
        pytest.param(replace(_REQUEST, python=Path("/other-python")), ReinstallReason.PYTHON, id="python"),
        pytest.param(replace(_REQUEST, backend="uv"), ReinstallReason.BACKEND, id="backend"),
        pytest.param(replace(_REQUEST, pip_args=("--pre",)), ReinstallReason.PIP_ARGS, id="pip-args"),
        pytest.param(
            replace(_REQUEST, venv_args=("--system-site-packages",)),
            ReinstallReason.VENV_ARGS,
            id="venv-args",
        ),
        pytest.param(
            replace(_REQUEST, include_dependencies=True),
            ReinstallReason.INCLUDE_DEPENDENCIES,
            id="include-dependencies",
        ),
    ],
)
def test_plan_tool_request_environment_drift_reinstalls(tool_request: ToolRequest, reason: ReinstallReason) -> None:
    assert plan_tool_request(tool_request, _STATE) == ReconcilePlan(ReconcileAction.REINSTALL, (reason,))
