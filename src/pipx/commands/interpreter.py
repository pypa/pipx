from __future__ import annotations

from pipx.animate import animate
from pipx.constants import ExitCode

__lazy_modules__ = [
    "packaging",
    "pipx",
    "pipx.commands.reinstall",
    "pipx.options",
    "pipx.paths",
    "pipx.pipx_metadata_file",
    "pipx.trash",
    "pipx.util",
    "pipx.venv",
    "subprocess",
]

import logging
import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from packaging import version

from pipx import constants
from pipx.commands.reinstall import reinstall
from pipx.options import ReinstallOptions
from pipx.paths import CTX
from pipx.pipx_metadata_file import PipxMetadata
from pipx.result import OperationData, OperationError, OperationResult, OutputLevel, OutputMessage, OutputStream
from pipx.trash import rmdir
from pipx.util import PipxError
from pipx.venv import Venv, VenvContainer

if TYPE_CHECKING:
    from pathlib import Path

    from filelock import BaseFileLock

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def list_interpreters(
    venv_container: VenvContainer,
) -> OperationResult[InterpreterData]:
    """List the standalone Python interpreters that pipx installed.

    :param venv_container: the container of the environments, to find which ones use each interpreter.
    :returns: the result listing the interpreters and the environments that use them.
    """
    venvs: Final[list[Venv]] = _venvs_using_standalone_interpreter(venv_container)
    output: Final[list[str]] = [f"Standalone interpreters are in {CTX.standalone_python_cachedir}"]
    listed: Final[list[_Interpreter]] = []
    for interpreter in _installed_standalone_interpreters():
        output.append(f"Python {interpreter.name}")
        if used_in := [venv.pipx_metadata for venv in _interpreter_users(interpreter, venvs)]:
            output.append("    Used in:")
            output.extend(f"     - {p.main_package.package} {p.main_package.package_version}" for p in used_in)
        else:
            output.append("    Unused")
        listed.append(
            _Interpreter(
                version=interpreter.name,
                used_by=tuple(str(metadata.main_package.package) for metadata in used_in),
            )
        )

    return OperationResult(
        command=("interpreter", "list"),
        data=InterpreterData(interpreters=tuple(listed), removed=(), upgraded=()),
        messages=(OutputMessage(text="\n".join(output)),),
    )


def _venvs_using_standalone_interpreter(venv_container: VenvContainer) -> list[Venv]:
    venvs: Final[list[Venv]] = []
    for venv_dir in venv_container.iter_venv_dirs():
        with venv_container.venv_lock(venv_dir):
            if (venv := Venv(venv_dir)).pipx_metadata.source_interpreter:
                venvs.append(venv)
    return venvs


def _installed_standalone_interpreters() -> list[Path]:
    # a dot-prefixed directory is the staging or backup copy of a fetch that may still be running, not an interpreter
    return [
        python_dir
        for python_dir in CTX.standalone_python_cachedir.iterdir()
        if python_dir.is_dir() and not python_dir.name.startswith(".")
    ]


def _interpreter_users(interpreter: Path, venvs: list[Venv]) -> list[Venv]:
    return [
        venv
        for venv in venvs
        if venv.pipx_metadata.source_interpreter and venv.pipx_metadata.source_interpreter.is_relative_to(interpreter)
    ]


@dataclass(frozen=True, slots=True, kw_only=True)
class _Interpreter:
    version: str
    used_by: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class InterpreterData(OperationData):
    """Result data of the interpreter commands.

    :ivar interpreters: the interpreters in use.
    :ivar removed: the names of the interpreters that were removed.
    :ivar upgraded: the interpreters that were upgraded.
    """

    interpreters: tuple[_Interpreter, ...]
    removed: tuple[str, ...]
    upgraded: tuple[_UpgradedInterpreter, ...]


def prune_interpreters(
    venv_container: VenvContainer,
) -> OperationResult[InterpreterData]:
    """Remove the standalone Python interpreters that no environment uses.

    :param venv_container: the container of the environments, to find which interpreters are in use.
    :returns: the result listing the removed interpreters.
    """
    venvs: Final[list[Venv]] = _venvs_using_standalone_interpreter(venv_container)
    removed: Final[list[str]] = []
    for interpreter in _installed_standalone_interpreters():
        if _interpreter_users(interpreter, venvs):
            continue
        rmdir(interpreter, safe_rm=True)
        removed.append(interpreter.name)
    report: Final[str] = (
        "\n".join(["Removed:", *(f" - Python {name}" for name in removed)]) if removed else "Nothing to remove"
    )
    return OperationResult(
        command=("interpreter", "prune"),
        data=InterpreterData(interpreters=(), removed=tuple(removed), upgraded=()),
        messages=(OutputMessage(text=report),),
    )


def upgrade_interpreters(venv_container: VenvContainer, *, verbose: bool) -> OperationResult[InterpreterData]:
    """Upgrade the standalone Python interpreters to their latest builds.

    :param venv_container: the container of the environments.
    :param verbose: show the progress of the index lookup.
    :returns: the result listing the upgraded interpreters.
    """
    from pipx import standalone_python  # ruff:ignore[import-outside-top-level]  # pulls in http.client, slows startup

    with animate("Getting the index of the latest standalone python builds", do_animation=not verbose):
        latest_pythons: Final[dict[str, tuple[str, str]]] = standalone_python.list_pythons(use_cache=False)

    parsed_latest_python_versions: Final[list[version.Version]] = [
        parsed for raw_version in latest_pythons if (parsed := _parse_python_version(raw_version)) is not None
    ]

    state: Final[_UpgradeState] = _UpgradeState()
    if upgrades := _build_upgrades(parsed_latest_python_versions, state):
        retry_only = all(upgrade.old_version == upgrade.new_version for upgrade in upgrades.values())
        for venv_dir in venv_container.iter_venv_dirs():
            # Metadata is replaced atomically. Check again under lock before rebuilding.
            if not retry_only or _pending_upgrade(PipxMetadata(venv_dir), upgrades) is not None:
                _upgrade_venv_interpreter(venv_container, venv_dir, upgrades, state, verbose=verbose)

    if state.upgraded:
        report = "\n".join([
            "Successfully upgraded the interpreter(s):",
            *(f" - {item.environment}: {item.old_version} -> {item.new_version}" for item in state.upgraded),
        ])
        state.messages.append(OutputMessage(text=report))
    elif not state.errors:
        state.messages.append(OutputMessage(text="Nothing to upgrade"))
    return OperationResult(
        command=("interpreter", "upgrade"),
        data=InterpreterData(
            interpreters=(),
            removed=(),
            upgraded=tuple(state.upgraded),
        ),
        messages=tuple(state.messages),
        exit_code=ExitCode(1 if state.errors else 0),
        errors=tuple(state.errors),
        succeeded=bool(state.upgraded),
    )


def _parse_python_version(raw_version: str) -> version.Version | None:
    try:
        return version.parse(raw_version)
    except version.InvalidVersion:
        _LOGGER.info("Invalid version found in latest pythons: %s. Skipping.", raw_version)
        return None


@dataclass(frozen=True, slots=True, kw_only=True)
class _UpgradeState:
    upgraded: list[_UpgradedInterpreter] = field(default_factory=list)
    errors: list[OperationError] = field(default_factory=list)
    messages: list[OutputMessage] = field(default_factory=list)


def _build_upgrades(latest_python_versions: list[version.Version], state: _UpgradeState) -> dict[str, _BuildUpgrade]:
    from pipx import standalone_python  # ruff:ignore[import-outside-top-level]  # pulls in http.client, slows startup

    # Downloading a minor build replaces it in place. Probe every cached build before any download.
    installed = {
        interpreter_dir.name: current
        for interpreter_dir in _installed_standalone_interpreters()
        if (current := _read_interpreter_version(interpreter_dir)) is not None
    }
    fetched: dict[tuple[int, int], str | None] = {}
    upgrades: dict[str, _BuildUpgrade] = {}
    for build, current in installed.items():
        latest = _latest_micro_version(current, latest_python_versions)
        minor = (latest.major, latest.minor)
        minor_name = f"{latest.major}.{latest.minor}"
        if latest <= current:
            if build == minor_name:
                # A previous invocation can replace the shared build before all rebuilds finish.
                python = str(_cached_interpreter_executable(CTX.standalone_python_cachedir / build))
                upgrades[build] = _BuildUpgrade(python=python, old_version=current, new_version=current)
            continue
        if minor not in fetched:
            try:
                fetched[minor] = standalone_python.download_python_build_standalone(
                    minor_name, override=installed.get(minor_name) != latest
                )
            except (OSError, PipxError) as error:
                _record_upgrade_error(error, subject=f"Python {latest}", environment=None, state=state)
                fetched[minor] = None
        if python := fetched[minor]:
            upgrades[build] = _BuildUpgrade(python=python, old_version=current, new_version=latest)
    return upgrades


def _read_interpreter_version(interpreter_dir: Path) -> version.Version | None:
    interpreter_python = _cached_interpreter_executable(interpreter_dir)
    try:
        reported = subprocess.run(
            [str(interpreter_python), "--version"], stdout=subprocess.PIPE, check=True, text=True
        ).stdout
        return version.parse(reported.removeprefix("Python ").strip())
    except (OSError, subprocess.CalledProcessError, version.InvalidVersion):
        _LOGGER.info("Cannot read the interpreter version at %s. Skipping.", interpreter_dir)
        return None


def _latest_micro_version(
    current_version: version.Version, latest_python_versions: list[version.Version]
) -> version.Version:
    for latest_python_version in latest_python_versions:
        if (
            current_version.major == latest_python_version.major
            and current_version.minor == latest_python_version.minor
        ):
            return latest_python_version
    return current_version


def _cached_interpreter_executable(interpreter_dir: Path) -> Path:
    return interpreter_dir / "python.exe" if constants.WINDOWS else interpreter_dir / "bin" / "python3"


@dataclass(frozen=True, slots=True, kw_only=True)
class _BuildUpgrade:
    python: str
    old_version: version.Version
    new_version: version.Version


def _record_upgrade_error(
    error: PipxError | OSError, *, subject: str, environment: str | None, state: _UpgradeState
) -> None:
    text = f"Could not upgrade {subject}. {error}"
    backend_output = error.backend_output if isinstance(error, PipxError) else ""
    state.errors.append(
        OperationError(
            code="interpreter_upgrade_failed",
            message=f"{text}\n{backend_output}" if backend_output else text,
            environment=environment,
        )
    )
    state.messages.append(OutputMessage(text=text, stream=OutputStream.STDERR, level=OutputLevel.ERROR))


def _pending_upgrade(
    metadata: PipxMetadata, upgrades: dict[str, _BuildUpgrade]
) -> tuple[_BuildUpgrade, version.Version] | None:
    source = metadata.source_interpreter
    if source is None or not source.is_relative_to(CTX.standalone_python_cachedir):
        return None
    if (upgrade := upgrades.get(next(iter(source.relative_to(CTX.standalone_python_cachedir).parts), ""))) is None:
        return None
    old = upgrade.old_version
    if isinstance(recorded := metadata.python_version, str):
        parsed = _parse_python_version(recorded.removeprefix("Python "))
        if parsed is not None and parsed.release[:2] == upgrade.new_version.release[:2]:
            old = parsed
    return (upgrade, old) if old < upgrade.new_version else None


def _upgrade_venv_interpreter(
    venv_container: VenvContainer,
    venv_dir: Path,
    upgrades: dict[str, _BuildUpgrade],
    state: _UpgradeState,
    *,
    verbose: bool,
) -> None:
    try:
        with venv_container.venv_lock(venv_dir) as venv_lock:
            _rebuild_venv(venv_dir, upgrades, state, venv_lock=venv_lock, verbose=verbose)
    except (OSError, PipxError) as error:
        _record_upgrade_error(error, subject=venv_dir.name, environment=venv_dir.name, state=state)


def _rebuild_venv(
    venv_dir: Path,
    upgrades: dict[str, _BuildUpgrade],
    state: _UpgradeState,
    *,
    venv_lock: BaseFileLock,
    verbose: bool,
) -> None:
    venv = Venv(venv_dir)
    if (pending := _pending_upgrade(venv.pipx_metadata, upgrades)) is None:
        return
    upgrade, old_version = pending
    _LOGGER.info("Upgrade the interpreter of %s from %s to %s", venv.name, old_version, upgrade.new_version)
    outcome = reinstall(
        venv_dir,
        ReinstallOptions(
            local_bin_dir=CTX.bin_dir,
            local_man_dir=CTX.man_dir,
            python=upgrade.python,
            verbose=verbose,
            # Requires-Python can reject this build, so do not fall back to a different interpreter.
            python_flag_passed=True,
        ),
        venv_lock=venv_lock,
    )
    if outcome.errors:
        state.errors.extend(outcome.errors)
        state.messages.extend(outcome.messages)
    else:
        state.upgraded.append(
            _UpgradedInterpreter(
                environment=venv.name, old_version=str(old_version), new_version=str(upgrade.new_version)
            )
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class _UpgradedInterpreter:
    environment: str
    old_version: str
    new_version: str


__all__ = [
    "InterpreterData",
    "list_interpreters",
    "prune_interpreters",
    "upgrade_interpreters",
]
