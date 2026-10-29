from __future__ import annotations

__lazy_modules__ = [
    "packaging",
    "pipx",
    "pipx.commands.reinstall",
    "pipx.options",
    "pipx.trash",
    "pipx.venv",
    "subprocess",
]

import logging
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from packaging import version

from pipx import constants, paths
from pipx.animate import animate
from pipx.commands.reinstall import reinstall
from pipx.options import ReinstallOptions
from pipx.result import OperationData, OperationResult, OutputMessage
from pipx.trash import rmdir
from pipx.venv import Venv, VenvContainer

if TYPE_CHECKING:
    from pathlib import Path

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def list_interpreters(
    venv_container: VenvContainer,
) -> OperationResult[InterpreterData]:
    venvs: Final[list[Venv]] = _venvs_using_standalone_interpreter(venv_container)
    output: Final[list[str]] = [f"Standalone interpreters are in {paths.CTX.standalone_python_cachedir}"]
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
        for python_dir in paths.CTX.standalone_python_cachedir.iterdir()
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
    interpreters: tuple[_Interpreter, ...]
    removed: tuple[str, ...]
    upgraded: tuple[_UpgradedInterpreter, ...]


def prune_interpreters(
    venv_container: VenvContainer,
) -> OperationResult[InterpreterData]:
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
    from pipx import standalone_python  # ruff:ignore[import-outside-top-level]  # pulls in http.client, slows startup

    with animate("Getting the index of the latest standalone python builds", do_animation=not verbose):
        latest_pythons: Final[dict[str, tuple[str, str]]] = standalone_python.list_pythons(use_cache=False)

    parsed_latest_python_versions: Final[list[version.Version]] = [
        parsed for raw_version in latest_pythons if (parsed := _parse_python_version(raw_version)) is not None
    ]

    upgraded: Final[list[tuple[str, str, version.Version]]] = []
    venvs: list[Venv] | None = None

    for interpreter_dir in _installed_standalone_interpreters():
        interpreter_python = (
            interpreter_dir / "python.exe" if constants.WINDOWS else interpreter_dir / "bin" / "python3"
        )
        try:
            interpreter_full_version = (
                subprocess
                .run([str(interpreter_python), "--version"], stdout=subprocess.PIPE, check=True, text=True)
                .stdout.removeprefix("Python ")
                .strip()
            )
            parsed_interpreter_full_version = version.parse(interpreter_full_version)
        except (OSError, subprocess.CalledProcessError, version.InvalidVersion):
            _LOGGER.info("Cannot read the interpreter version at %s. Skipping.", interpreter_dir)
            continue
        latest_micro_version = _latest_micro_version(parsed_interpreter_full_version, parsed_latest_python_versions)
        if latest_micro_version > parsed_interpreter_full_version:
            # the new build lands in py/X.Y, so venvs on a patch-pinned py/X.Y.Z build must move to it
            upgraded_python = standalone_python.download_python_build_standalone(
                f"{latest_micro_version.major}.{latest_micro_version.minor}",
                override=True,
            )

            if venvs is None:
                venvs = _venvs_using_standalone_interpreter(venv_container)
            for venv in _interpreter_users(interpreter_dir, venvs):
                with venv_container.venv_lock(venv.root) as venv_lock:
                    _LOGGER.info(
                        "Upgrade the interpreter of %s from %s to %s",
                        venv.name,
                        interpreter_full_version,
                        latest_micro_version,
                    )
                    reinstall(
                        venv.root,
                        ReinstallOptions(
                            local_bin_dir=paths.CTX.bin_dir,
                            local_man_dir=paths.CTX.man_dir,
                            python=upgraded_python,
                            verbose=verbose,
                            # the new build is what this rebuild is for, so a package whose Requires-Python rules it
                            # out fails (and keeps its environment) instead of moving to another Python from PATH
                            python_flag_passed=True,
                        ),
                        venv_lock=venv_lock,
                    )
                    upgraded.append((venv.name, interpreter_full_version, latest_micro_version))

    if upgraded:
        report = "\n".join([
            "Successfully upgraded the interpreter(s):",
            *(f" - {name}: {old} -> {new}" for name, old, new in upgraded),
        ])
    else:
        report = "Nothing to upgrade"
    return OperationResult(
        command=("interpreter", "upgrade"),
        data=InterpreterData(
            interpreters=(),
            removed=(),
            upgraded=tuple(
                _UpgradedInterpreter(environment=name, old_version=old, new_version=str(new))
                for name, old, new in upgraded
            ),
        ),
        messages=(OutputMessage(text=report),),
    )


def _parse_python_version(raw_version: str) -> version.Version | None:
    try:
        return version.parse(raw_version)
    except version.InvalidVersion:
        _LOGGER.info("Invalid version found in latest pythons: %s. Skipping.", raw_version)
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
