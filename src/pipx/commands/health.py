from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from pipx.commands.reinstall import reinstall
from pipx.constants import ExitCode
from pipx.result import OperationData, OperationError, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.util import PipxError, get_venv_paths, run_subprocess

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from pipx.venv import VenvContainer


def health(venv_container: VenvContainer, venv_dirs: Iterable[Path]) -> OperationResult[HealthData]:
    environments: list[_EnvironmentHealth] = []
    messages: list[OutputMessage] = []
    for venv_dir in venv_dirs:
        with venv_container.venv_lock(venv_dir):
            environment = _check_health(venv_dir)
        environments.append(environment)
        if environment.status is _HealthStatus.HEALTHY:
            messages.append(OutputMessage(f"{environment.environment}: healthy"))
            continue
        location = f" at {environment.interpreter}" if environment.interpreter else ""
        messages.append(OutputMessage(f"{environment.environment}: {environment.error}{location}"))
    if not messages:
        messages.append(OutputMessage("pipx manages no packages."))
    return OperationResult(
        command=("health",),
        data=HealthData(environments=tuple(environments)),
        messages=tuple(messages),
        exit_code=ExitCode(
            1 if any(environment.status is not _HealthStatus.HEALTHY for environment in environments) else 0
        ),
    )


def repair(  # noqa: PLR0913  # repair forwards the full reinstall context to every broken environment
    venv_container: VenvContainer,
    venv_dirs: Iterable[Path],
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str,
    *,
    verbose: bool,
    python_flag_passed: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
) -> OperationResult[RepairData]:
    failures: list[_FailedRepair] = []
    messages: list[OutputMessage] = []
    repaired: list[_RepairedEnvironment] = []
    skipped: list[_SkippedRepair] = []
    for venv_dir in venv_dirs:
        with venv_container.venv_lock(venv_dir) as venv_lock:
            environment = _check_health(venv_dir)
            if environment.status is _HealthStatus.HEALTHY:
                skipped.append(_SkippedRepair(venv_dir.name, "healthy"))
                messages.append(OutputMessage(f"{venv_dir.name}: healthy"))
                continue
            if environment.status is _HealthStatus.MISSING:
                failure = _FailedRepair(venv_dir.name, environment.error or "environment is missing")
                failures.append(failure)
                messages.append(_repair_failure_message(failure))
                continue
            try:
                reinstall(
                    venv_dir=venv_dir,
                    local_bin_dir=local_bin_dir,
                    local_man_dir=local_man_dir,
                    python=python,
                    verbose=verbose,
                    python_flag_passed=python_flag_passed,
                    backend=backend,
                    env_backend=env_backend,
                    venv_lock=venv_lock,
                )
            except PipxError as error:
                failure = _FailedRepair(venv_dir.name, str(error))
                failures.append(failure)
                messages.append(_repair_failure_message(failure))
                continue
            if (environment := _check_health(venv_dir)).status is not _HealthStatus.HEALTHY:
                failure = _FailedRepair(venv_dir.name, environment.error or "interpreter remains broken")
                failures.append(failure)
                messages.append(_repair_failure_message(failure))
                continue
            repaired.append(_RepairedEnvironment(venv_dir.name, environment.interpreter))
            messages.append(OutputMessage(f"{venv_dir.name}: repaired"))

    if not messages:
        messages.append(OutputMessage("pipx found no environments to repair."))
    return OperationResult(
        command=("repair",),
        data=RepairData(repaired=tuple(repaired), skipped=tuple(skipped)),
        messages=tuple(messages),
        exit_code=ExitCode(1 if failures else 0),
        errors=tuple(
            OperationError(code="environment_repair_failed", message=failure.error, environment=failure.environment)
            for failure in failures
        ),
        succeeded=bool(repaired),
    )


def _check_health(venv_dir: Path) -> _EnvironmentHealth:
    if not venv_dir.is_dir():
        return _EnvironmentHealth(venv_dir.name, "", _HealthStatus.MISSING, "pipx does not manage this environment")

    _, interpreter, _ = get_venv_paths(venv_dir)
    if not interpreter.is_file():
        return _EnvironmentHealth(venv_dir.name, str(interpreter), _HealthStatus.BROKEN, "interpreter is missing")
    try:
        process = run_subprocess([interpreter, "--version"], log_stdout=False, log_stderr=False)
    except OSError as error:
        return _EnvironmentHealth(
            venv_dir.name,
            str(interpreter),
            _HealthStatus.BROKEN,
            f"interpreter could not start: {error.strerror or error}",
        )
    if process.returncode:
        return _EnvironmentHealth(
            venv_dir.name,
            str(interpreter),
            _HealthStatus.BROKEN,
            f"interpreter exited with status {process.returncode}",
        )
    return _EnvironmentHealth(venv_dir.name, str(interpreter), _HealthStatus.HEALTHY, None)


def _repair_failure_message(failure: _FailedRepair) -> OutputMessage:
    return OutputMessage(
        f"{failure.environment}: {failure.error}",
        stream=OutputStream.STDERR,
        level=OutputLevel.ERROR,
    )


class _HealthStatus(str, Enum):
    HEALTHY = "healthy"
    BROKEN = "broken"
    MISSING = "missing"


@dataclass(frozen=True)
class _EnvironmentHealth:
    environment: str
    interpreter: str
    status: _HealthStatus
    error: str | None


@dataclass(frozen=True)
class HealthData(OperationData):
    environments: tuple[_EnvironmentHealth, ...]


@dataclass(frozen=True)
class _RepairedEnvironment:
    environment: str
    interpreter: str


@dataclass(frozen=True)
class _SkippedRepair:
    environment: str
    reason: str


@dataclass(frozen=True)
class _FailedRepair:
    environment: str
    error: str


@dataclass(frozen=True)
class RepairData(OperationData):
    repaired: tuple[_RepairedEnvironment, ...]
    skipped: tuple[_SkippedRepair, ...]


__all__ = [
    "HealthData",
    "RepairData",
    "health",
    "repair",
]
