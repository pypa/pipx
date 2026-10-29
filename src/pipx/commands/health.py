from __future__ import annotations

__lazy_modules__ = ["pipx.commands.reinstall", "pipx.subprocess_runner", "pipx.util"]

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from pipx.commands.reinstall import reinstall
from pipx.constants import ExitCode
from pipx.result import OperationData, OperationError, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.subprocess_runner import run_subprocess
from pipx.util import PipxError, get_venv_paths

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from pipx.options import ReinstallOptions
    from pipx.venv import VenvContainer


def health(venv_container: VenvContainer, venv_dirs: Iterable[Path]) -> OperationResult[HealthData]:
    environments: Final[list[_EnvironmentHealth]] = []
    messages: Final[list[OutputMessage]] = []
    for venv_dir in venv_dirs:
        with venv_container.venv_lock(venv_dir):
            environment: Final[_EnvironmentHealth] = _check_health(venv_dir)
        environments.append(environment)
        if environment.status is _HealthStatus.HEALTHY:
            messages.append(OutputMessage(text=f"{environment.environment}: healthy"))
            continue
        location: Final[str] = f" at {environment.interpreter}" if environment.interpreter else ""
        messages.append(OutputMessage(text=f"{environment.environment}: {environment.error}{location}"))
    if not messages:
        messages.append(OutputMessage(text="pipx manages no packages."))
    errors: Final[tuple[OperationError, ...]] = tuple(
        OperationError(code="environment_unhealthy", message=environment.error, environment=environment.environment)
        for environment in environments
        if environment.error is not None
    )
    return OperationResult(
        command=("health",),
        data=HealthData(environments=tuple(environments)),
        messages=tuple(messages),
        exit_code=ExitCode(1 if errors else 0),
        errors=errors,
        succeeded=any(environment.status is _HealthStatus.HEALTHY for environment in environments),
    )


def _check_health(venv_dir: Path) -> _EnvironmentHealth:
    if not venv_dir.is_dir():
        return _EnvironmentHealth(
            environment=venv_dir.name,
            interpreter="",
            status=_HealthStatus.MISSING,
            error="pipx does not manage this environment",
        )

    _, interpreter, _ = get_venv_paths(venv_dir)
    if not interpreter.is_file():
        return _EnvironmentHealth(
            environment=venv_dir.name,
            interpreter=str(interpreter),
            status=_HealthStatus.BROKEN,
            error="interpreter is missing",
        )
    try:
        process: Final = run_subprocess([interpreter, "--version"], log_stdout=False, log_stderr=False)
    except OSError as error:
        return _EnvironmentHealth(
            environment=venv_dir.name,
            interpreter=str(interpreter),
            status=_HealthStatus.BROKEN,
            error=f"interpreter could not start: {error.strerror or error}",
        )
    if process.returncode:
        return _EnvironmentHealth(
            environment=venv_dir.name,
            interpreter=str(interpreter),
            status=_HealthStatus.BROKEN,
            error=f"interpreter exited with status {process.returncode}",
        )
    return _EnvironmentHealth(
        environment=venv_dir.name, interpreter=str(interpreter), status=_HealthStatus.HEALTHY, error=None
    )


class _HealthStatus(StrEnum):
    HEALTHY = "healthy"
    BROKEN = "broken"
    MISSING = "missing"


@dataclass(frozen=True, slots=True, kw_only=True)
class _EnvironmentHealth:
    environment: str
    interpreter: str
    status: _HealthStatus
    error: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class HealthData(OperationData):
    environments: tuple[_EnvironmentHealth, ...]


def repair(
    venv_container: VenvContainer, venv_dirs: Iterable[Path], options: ReinstallOptions
) -> OperationResult[RepairData]:
    failures: Final[list[_FailedRepair]] = []
    messages: Final[list[OutputMessage]] = []
    repaired: Final[list[_RepairedEnvironment]] = []
    skipped: Final[list[_SkippedRepair]] = []
    for venv_dir in venv_dirs:
        with venv_container.venv_lock(venv_dir) as venv_lock:
            environment = _check_health(venv_dir)
            if environment.status is _HealthStatus.HEALTHY:
                skipped.append(_SkippedRepair(environment=venv_dir.name, reason="healthy"))
                messages.append(OutputMessage(text=f"{venv_dir.name}: healthy"))
                continue
            if environment.status is _HealthStatus.MISSING:
                error = environment.error or "environment is missing"
            else:
                try:
                    reinstall(venv_dir, options, venv_lock=venv_lock)
                except PipxError as reinstall_error:
                    error = str(reinstall_error)
                else:
                    if (environment := _check_health(venv_dir)).status is _HealthStatus.HEALTHY:
                        repaired.append(
                            _RepairedEnvironment(environment=venv_dir.name, interpreter=environment.interpreter)
                        )
                        messages.append(OutputMessage(text=f"{venv_dir.name}: repaired"))
                        continue
                    error = environment.error or "interpreter remains broken"
            failures.append(_FailedRepair(environment=venv_dir.name, error=error))
            messages.append(
                OutputMessage(text=f"{venv_dir.name}: {error}", stream=OutputStream.STDERR, level=OutputLevel.ERROR)
            )

    if not messages:
        messages.append(OutputMessage(text="pipx found no environments to repair."))
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


@dataclass(frozen=True, slots=True, kw_only=True)
class _SkippedRepair:
    environment: str
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _RepairedEnvironment:
    environment: str
    interpreter: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _FailedRepair:
    environment: str
    error: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RepairData(OperationData):
    repaired: tuple[_RepairedEnvironment, ...]
    skipped: tuple[_SkippedRepair, ...]


__all__ = [
    "HealthData",
    "RepairData",
    "health",
    "repair",
]
