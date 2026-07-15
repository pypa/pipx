from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from packaging import version

from pipx import commands, constants, paths, standalone_python
from pipx.animate import animate
from pipx.result import OperationData, OperationResult, OutputMessage
from pipx.util import is_paths_relative, rmdir
from pipx.venv import Venv, VenvContainer

if TYPE_CHECKING:
    from pathlib import Path

    from pipx.pipx_metadata_file import PipxMetadata

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def get_installed_standalone_interpreters() -> list[Path]:
    return [python_dir for python_dir in paths.ctx.standalone_python_cachedir.iterdir() if python_dir.is_dir()]


def get_venvs_using_standalone_interpreter(venv_container: VenvContainer) -> list[Venv]:
    venvs: list[Venv] = []
    for venv_dir in venv_container.iter_venv_dirs():
        with venv_container.venv_lock(venv_dir):
            venv = Venv(venv_dir)
            if venv.pipx_metadata.source_interpreter:
                venvs.append(venv)
    return venvs


def get_interpreter_users(interpreter: Path, venvs: list[Venv]) -> list[PipxMetadata]:
    return [
        venv.pipx_metadata
        for venv in venvs
        if venv.pipx_metadata.source_interpreter
        and is_paths_relative(venv.pipx_metadata.source_interpreter, interpreter)
    ]


def list_interpreters(
    venv_container: VenvContainer,
) -> OperationResult[InterpreterData]:
    interpreters = get_installed_standalone_interpreters()
    venvs = get_venvs_using_standalone_interpreter(venv_container)
    output: list[str] = [f"Standalone interpreters are in {paths.ctx.standalone_python_cachedir}"]
    listed: list[_Interpreter] = []
    for interpreter in interpreters:
        output.append(f"Python {interpreter.name}")
        used_in = get_interpreter_users(interpreter, venvs)
        if used_in:
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
        messages=(OutputMessage("\n".join(output)),),
    )


def prune_interpreters(
    venv_container: VenvContainer,
) -> OperationResult[InterpreterData]:
    interpreters = get_installed_standalone_interpreters()
    venvs = get_venvs_using_standalone_interpreter(venv_container)
    removed = []
    for interpreter in interpreters:
        if get_interpreter_users(interpreter, venvs):
            continue
        rmdir(interpreter, safe_rm=True)
        removed.append(interpreter.name)
    if removed:
        report = "\n".join(["Successfully removed:", *(f" - Python {name}" for name in removed)])
    else:
        report = "Nothing to remove"
    return OperationResult(
        command=("interpreter", "prune"),
        data=InterpreterData(interpreters=(), removed=tuple(removed), upgraded=()),
        messages=(OutputMessage(report),),
    )


def _parse_python_version(raw_version: str) -> version.Version | None:
    try:
        return version.parse(raw_version)
    except version.InvalidVersion:
        _LOGGER.info("Invalid version found in latest pythons: %s. Skipping.", raw_version)
        return None


def get_latest_micro_version(
    current_version: version.Version, latest_python_versions: list[version.Version]
) -> version.Version:
    for latest_python_version in latest_python_versions:
        if (
            current_version.major == latest_python_version.major
            and current_version.minor == latest_python_version.minor
        ):
            return latest_python_version
    return current_version


def upgrade_interpreters(venv_container: VenvContainer, *, verbose: bool) -> OperationResult[InterpreterData]:
    with animate("Getting the index of the latest standalone python builds", do_animation=not verbose):
        latest_pythons = standalone_python.list_pythons(use_cache=False)

    parsed_latest_python_versions = [
        parsed for raw_version in latest_pythons if (parsed := _parse_python_version(raw_version)) is not None
    ]

    upgraded = []
    venvs: list[Venv] | None = None

    for interpreter_dir in paths.ctx.standalone_python_cachedir.iterdir():
        if not interpreter_dir.is_dir():
            continue

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
        latest_micro_version = get_latest_micro_version(parsed_interpreter_full_version, parsed_latest_python_versions)
        if latest_micro_version > parsed_interpreter_full_version:
            standalone_python.download_python_build_standalone(
                f"{latest_micro_version.major}.{latest_micro_version.minor}",
                override=True,
            )

            if venvs is None:
                venvs = get_venvs_using_standalone_interpreter(venv_container)
            for venv in venvs:
                if venv.pipx_metadata.source_interpreter is not None and is_paths_relative(
                    venv.pipx_metadata.source_interpreter, interpreter_dir
                ):
                    with venv_container.venv_lock(venv.root) as venv_lock:
                        _LOGGER.info(
                            "Upgrade the interpreter of %s from %s to %s",
                            venv.name,
                            interpreter_full_version,
                            latest_micro_version,
                        )
                        commands.reinstall(
                            venv_dir=venv.root,
                            local_bin_dir=paths.ctx.bin_dir,
                            local_man_dir=paths.ctx.man_dir,
                            python=str(interpreter_python),
                            verbose=verbose,
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
            upgraded=tuple(_UpgradedInterpreter(name, old, str(new)) for name, old, new in upgraded),
        ),
        messages=(OutputMessage(report),),
    )


@dataclass(frozen=True)
class _Interpreter:
    version: str
    used_by: tuple[str, ...]


@dataclass(frozen=True)
class _UpgradedInterpreter:
    environment: str
    old_version: str
    new_version: str


@dataclass(frozen=True)
class InterpreterData(OperationData):
    interpreters: tuple[_Interpreter, ...]
    removed: tuple[str, ...]
    upgraded: tuple[_UpgradedInterpreter, ...]


__all__ = [
    "InterpreterData",
    "list_interpreters",
    "prune_interpreters",
    "upgrade_interpreters",
]
