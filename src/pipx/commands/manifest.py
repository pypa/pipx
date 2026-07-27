from __future__ import annotations

import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time
from importlib import import_module
from pathlib import Path
from shutil import copy2, which
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Final, TypeAlias, cast

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from pipx.commands.expose import expose, unexpose
from pipx.commands.install import install
from pipx.commands.uninstall import uninstall
from pipx.constants import EXIT_CODE_OK, ExitCode
from pipx.pipx_metadata_file import PipxMetadata
from pipx.result import (
    OperationData,
    OperationError,
    OperationResult,
    OutputLevel,
    OutputMessage,
    OutputStream,
)
from pipx.util import PipxError

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib

    from pipx.venv import VenvContainer
else:
    tomllib = import_module("tomli" if sys.version_info < (3, 11) else "tomllib")


def sync_manifest(  # ruff:ignore[too-many-arguments]  # manifest sync forwards the full install context for each tool
    manifest_file: Path,
    venv_container: VenvContainer,
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str,
    *,
    verbose: bool,
    prune: bool,
    backend: str | None,
    env_backend: str | None,
) -> OperationResult[ManifestData]:
    manifest = _load_manifest(manifest_file, require_locks=True)
    failures: list[_FailedTool] = []
    messages: list[OutputMessage] = []
    synced: list[str] = []
    for tool in manifest.tools:
        venv_dir = venv_container.get_venv_dir(tool.environment)
        with venv_container.venv_lock(venv_dir) as venv_lock:
            existed = venv_dir.is_dir()
            was_exposed = existed and PipxMetadata(venv_dir).exposure_enabled
            if was_exposed:
                unexpose(venv_dir, local_bin_dir, local_man_dir, verbose=verbose)
            try:
                outcome = install(
                    venv_dir,
                    [tool.package_name],
                    [tool.package],
                    local_bin_dir,
                    local_man_dir,
                    python,
                    [],
                    [],
                    verbose=verbose,
                    force=existed,
                    reinstall=False,
                    include_dependencies=tool.include_dependencies,
                    include_resources_from=tool.include_resources_from,
                    preinstall_packages=None,
                    expected_apps=tool.apps,
                    lock_file=tool.lock_file,
                    suffix=tool.suffix,
                    backend=backend,
                    env_backend=env_backend,
                    exposure_enabled=tool.expose,
                    preserve_existing=True,
                    replace_expected_apps=True,
                    replace_lock=True,
                    venv_lock=venv_lock,
                    emit_output=False,
                )
                error_message = outcome.errors[0].message if outcome.errors else None
            except PipxError as error:
                error_message = str(error)
            # install returns a failed result rather than raising when it does not render, so check both
            if error_message is not None:
                failures.append(_FailedTool(tool.environment, error_message))
                messages.append(OutputMessage(error_message, stream=OutputStream.STDERR, level=OutputLevel.ERROR))
                if was_exposed:
                    expose(venv_dir, local_bin_dir, local_man_dir, verbose=verbose)
            else:
                synced.append(tool.environment)

    if prune and not failures:
        messages.extend(_prune_environments(manifest, venv_container, local_bin_dir, local_man_dir, verbose=verbose))
    return OperationResult(
        command=("manifest", "sync"),
        data=ManifestData(environments=tuple(synced), locks=()),
        messages=tuple(messages),
        exit_code=ExitCode(1) if failures else EXIT_CODE_OK,
        errors=tuple(
            OperationError(code="manifest_sync_failed", message=f.error, environment=f.environment) for f in failures
        ),
        succeeded=bool(synced),
    )


def lock_manifest(manifest_file: Path) -> OperationResult[ManifestData]:
    manifest = _load_manifest(manifest_file, require_locks=False)
    if not any(tool.lock_file is not None for tool in manifest.tools):
        msg = "The manifest does not declare any lock files."
        raise PipxError(msg)
    if not (nab := which("nab")):
        msg = "The nab command is required. Install it with `pipx install nab`."
        raise PipxError(msg)
    try:
        locked: Final[list[str]] = _generate_locks(manifest, nab)
    except OSError as error:
        msg = f"Cannot write manifest locks: {error}"
        raise PipxError(msg) from error
    return OperationResult(
        command=("manifest", "lock"),
        data=ManifestData(environments=(), locks=tuple(locked)),
        messages=tuple(OutputMessage(f"locked {lock_file}") for lock_file in locked),
    )


def _load_manifest(manifest_file: Path, *, require_locks: bool) -> _Manifest:
    path = manifest_file.expanduser().resolve()
    try:
        with path.open("rb") as file:
            data = cast("dict[str, _TomlValue]", tomllib.load(file))
    except FileNotFoundError as error:
        msg = f"Manifest does not exist: {path}"
        raise PipxError(msg) from error
    except (OSError, tomllib.TOMLDecodeError) as error:
        msg = f"Cannot read manifest {path}: {error}"
        raise PipxError(msg) from error

    groups, tool_data = _parse_manifest_tables(data)

    tools: list[_ManifestTool] = []
    for environment, group in groups.items():
        if not isinstance(group, list) or len(group) != 1 or not isinstance(package := group[0], str):
            msg = f"Dependency group {environment} must contain one package requirement."
            raise PipxError(msg)
        if not isinstance(values := tool_data.get(environment, {}), dict):
            msg = f"Manifest tool {environment} must be a table."
            raise PipxError(msg)
        tools.append(_parse_tool(environment, package, values, path.parent, require_locks=require_locks))
    if duplicates := _duplicate_lock_files(tools):
        msg = f"Lock files must be unique per tool: {', '.join(map(str, duplicates))}"
        raise PipxError(msg)
    return _Manifest(path=path, tools=tuple(tools))


def _parse_manifest_tables(
    data: dict[str, _TomlValue],
) -> tuple[dict[str, _TomlValue], dict[str, _TomlValue]]:
    if unknown := sorted(set(data) - _ROOT_KEYS):
        msg = f"Unknown manifest {'table' if len(unknown) == 1 else 'tables'}: {', '.join(unknown)}"
        raise PipxError(msg)
    if not isinstance(project := data.get("project"), dict):
        msg = "Manifest project must be a table."
        raise PipxError(msg)
    _validate_project(project)
    if not isinstance(groups := data.get("dependency-groups"), dict) or not groups:
        msg = "Manifest dependency-groups must be a non-empty table."
        raise PipxError(msg)
    if not isinstance(tool_table := data.get("tool"), dict):
        msg = "Manifest tool must be a table."
        raise PipxError(msg)
    if unknown := sorted(set(tool_table) - _TOOL_TABLE_KEYS):
        msg = f"Unknown manifest tool {'table' if len(unknown) == 1 else 'tables'}: {', '.join(unknown)}"
        raise PipxError(msg)
    if (nab_data := tool_table.get("nab")) is not None and not isinstance(nab_data, dict):
        msg = "Manifest tool.nab must be a table."
        raise PipxError(msg)
    return groups, _parse_pipx_table(tool_table, groups)


def _validate_project(data: dict[str, _TomlValue]) -> None:
    if unknown := sorted(set(data) - _PROJECT_KEYS):
        msg = f"Unknown manifest project {'key' if len(unknown) == 1 else 'keys'}: {', '.join(unknown)}"
        raise PipxError(msg)
    if not isinstance(data.get("name"), str) or not isinstance(data.get("version"), str):
        msg = "Manifest project requires string name and version values."
        raise PipxError(msg)
    if data.get("dependencies") != []:
        msg = "Manifest project dependencies must be empty; declare tools in dependency-groups."
        raise PipxError(msg)
    if (requires_python := data.get("requires-python")) is not None and not isinstance(requires_python, str):
        msg = "Manifest project requires-python must be a string."
        raise PipxError(msg)


def _parse_pipx_table(
    tool_table: dict[str, _TomlValue],
    groups: dict[str, _TomlValue],
) -> dict[str, _TomlValue]:
    if not isinstance(pipx_data := tool_table.get("pipx"), dict):
        msg = "Manifest tool.pipx must be a table."
        raise PipxError(msg)
    if unknown := sorted(set(pipx_data) - _PIPX_KEYS):
        msg = f"Unknown tool.pipx {'key' if len(unknown) == 1 else 'keys'}: {', '.join(unknown)}"
        raise PipxError(msg)
    if pipx_data.get("version") != _MANIFEST_VERSION:
        msg = f'Manifest version must be "{_MANIFEST_VERSION}".'
        raise PipxError(msg)
    if not isinstance(tool_data := pipx_data.get("tools", {}), dict):
        msg = "Manifest tool.pipx.tools must be a table."
        raise PipxError(msg)
    if unknown := sorted(set(tool_data) - set(groups)):
        msg = f"Missing dependency groups for manifest tools: {', '.join(unknown)}"
        raise PipxError(msg)
    return tool_data


def _parse_tool(
    environment: str,
    package: str,
    data: dict[str, _TomlValue],
    manifest_dir: Path,
    *,
    require_locks: bool,
) -> _ManifestTool:
    if environment != canonicalize_name(environment):
        msg = f"Manifest tool name must be normalized: {environment}"
        raise PipxError(msg)
    if unknown := sorted(set(data) - _TOOL_KEYS):
        msg = f"Unknown {'key' if len(unknown) == 1 else 'keys'} for manifest tool {environment}: {', '.join(unknown)}"
        raise PipxError(msg)
    package_name = _parse_package(environment, package)
    if not isinstance(suffix := data.get("suffix", ""), str):
        msg = f"Manifest tool {environment} suffix must be a string."
        raise PipxError(msg)
    if environment != canonicalize_name(f"{package_name}{suffix}"):
        msg = f"Manifest tool {environment} must match package {package_name} and suffix {suffix!r}."
        raise PipxError(msg)
    if not isinstance(include_dependencies := data.get("include-dependencies", False), bool):
        msg = f"Manifest tool {environment} include-dependencies must be a boolean."
        raise PipxError(msg)
    include_resources_from: Final[tuple[str, ...]] = _parse_include_resources_from(environment, data)
    if include_dependencies and include_resources_from:
        msg = f"Manifest tool {environment} cannot combine include-dependencies with include-resources-from."
        raise PipxError(msg)
    if not isinstance(expose_resources := data.get("expose", True), bool):
        msg = f"Manifest tool {environment} expose must be a boolean."
        raise PipxError(msg)

    return _ManifestTool(
        environment=environment,
        package=package,
        package_name=package_name,
        suffix=suffix,
        apps=_parse_apps(environment, data),
        include_dependencies=include_dependencies,
        include_resources_from=include_resources_from,
        expose=expose_resources,
        lock_file=_parse_lock_file(environment, data, manifest_dir, require_locks=require_locks),
    )


def _parse_package(environment: str, package: str) -> str:
    try:
        requirement = Requirement(package)
    except InvalidRequirement as error:
        msg = f"Manifest tool {environment} has an invalid package requirement: {package}"
        raise PipxError(msg) from error
    if requirement.marker is not None:
        msg = f"Manifest tool {environment} cannot use an environment marker."
        raise PipxError(msg)
    return canonicalize_name(requirement.name)


def _parse_include_resources_from(environment: str, data: dict[str, _TomlValue]) -> tuple[str, ...]:
    if not isinstance(packages := data.get("include-resources-from", []), list) or any(
        not isinstance(package, str) or not package for package in packages
    ):
        msg = f"Manifest tool {environment} include-resources-from must be non-empty strings."
        raise PipxError(msg)
    included: Final[tuple[str, ...]] = tuple(canonicalize_name(package) for package in cast("list[str]", packages))
    if len(included) != len(set(included)):
        msg = f"Manifest tool {environment} include-resources-from must be unique."
        raise PipxError(msg)
    return included


def _parse_apps(environment: str, data: dict[str, _TomlValue]) -> tuple[str, ...]:
    if not isinstance(apps := data.get("apps", []), list) or any(not isinstance(app, str) or not app for app in apps):
        msg = f"Manifest tool {environment} apps must be non-empty strings."
        raise PipxError(msg)
    if len(apps) != len(set(apps)):
        msg = f"Manifest tool {environment} apps must be unique."
        raise PipxError(msg)
    return tuple(cast("list[str]", apps))


def _parse_lock_file(
    environment: str,
    data: dict[str, _TomlValue],
    manifest_dir: Path,
    *,
    require_locks: bool,
) -> Path | None:
    if (lock_value := data.get("lock")) is None:
        return None
    if not isinstance(lock_value, str):
        msg = f"Manifest tool {environment} lock must be a path string."
        raise PipxError(msg)
    lock_file = Path(lock_value).expanduser()
    if not lock_file.is_absolute():
        lock_file = manifest_dir / lock_file
    lock_file = lock_file.resolve()
    if not _is_pylock_name(lock_file.name):
        msg = f"Manifest tool {environment} lock must be named pylock.toml or pylock.<name>.toml."
        raise PipxError(msg)
    if require_locks and not lock_file.is_file():
        msg = f"Lock file does not exist for manifest tool {environment}: {lock_file}"
        raise PipxError(msg)
    return lock_file


def _duplicate_lock_files(tools: list[_ManifestTool]) -> tuple[Path, ...]:
    counts = Counter(tool.lock_file for tool in tools if tool.lock_file is not None)
    return tuple(sorted(lock_file for lock_file, count in counts.items() if count > 1))


def _is_pylock_name(name: str) -> bool:
    if name == "pylock.toml":
        return True
    return (
        name.startswith("pylock.")
        and name.endswith(".toml")
        and bool(lock_name := name.removeprefix("pylock.").removesuffix(".toml"))
        and "." not in lock_name
    )


def _generate_locks(manifest: _Manifest, nab: str) -> list[str]:
    with TemporaryDirectory(prefix=".pipx-lock-", dir=manifest.path.parent) as temporary_dir:
        generated: list[tuple[Path, Path]] = []
        for tool in manifest.tools:
            if tool.lock_file is None:
                continue
            tool_dir = Path(temporary_dir) / tool.environment
            tool_dir.mkdir()
            generated_lock = tool_dir / tool.lock_file.name
            if tool.lock_file.is_file():
                copy2(tool.lock_file, generated_lock)
            if subprocess.run(
                [
                    nab,
                    "lock",
                    str(manifest.path),
                    "--groups",
                    tool.environment,
                    "--output",
                    str(generated_lock),
                ],
                check=False,
                cwd=manifest.path.parent,
            ).returncode:
                msg = f"nab failed to lock {tool.environment}."
                raise PipxError(msg)
            if not generated_lock.is_file():
                msg = f"nab did not create {generated_lock.name} for {tool.environment}."
                raise PipxError(msg)
            generated.append((generated_lock, tool.lock_file))

        backups_dir = Path(temporary_dir) / ".previous"
        backups_dir.mkdir()
        locked: Final[list[str]] = []
        # replacing the whole set one file at a time is not atomic, so back each target up first and, if any replacement
        # fails, roll every applied one back to leave the manifest's locks all-old rather than half-new
        applied: list[tuple[Path, Path | None]] = []
        try:  # ruff:ignore[too-many-statements-in-try-clause]  # the whole apply loop shares one handler so a mid-run failure rolls all locks back
            for index, (generated_lock, lock_file) in enumerate(generated):
                lock_file.parent.mkdir(parents=True, exist_ok=True)
                backup: Path | None = None
                if lock_file.is_file():
                    backup = backups_dir / f"{index}-{lock_file.name}"
                    lock_file.replace(backup)
                # record before the swap-in so a failure mid-replacement still rolls this target back
                applied.append((lock_file, backup))
                generated_lock.replace(lock_file)
                locked.append(str(lock_file))
        except OSError:
            for lock_file, backup in reversed(applied):
                if backup is not None:
                    backup.replace(lock_file)
                else:
                    lock_file.unlink(missing_ok=True)
            raise
    return locked


def _prune_environments(
    manifest: _Manifest,
    venv_container: VenvContainer,
    local_bin_dir: Path,
    local_man_dir: Path,
    *,
    verbose: bool,
) -> list[OutputMessage]:
    declared = {tool.environment for tool in manifest.tools}
    messages: list[OutputMessage] = []
    for venv_dir in sorted(venv_container.iter_venv_dirs()):
        if venv_dir.name in declared:
            continue
        with venv_container.venv_lock(venv_dir):
            messages.extend(uninstall(venv_dir, local_bin_dir, local_man_dir, verbose=verbose).messages)
    return messages


@dataclass(frozen=True)
class _Manifest:
    path: Path
    tools: tuple[_ManifestTool, ...]


@dataclass(frozen=True)
class _ManifestTool:
    environment: str
    package: str
    package_name: str
    suffix: str
    apps: tuple[str, ...]
    include_dependencies: bool
    include_resources_from: tuple[str, ...]
    expose: bool
    lock_file: Path | None


_TomlValue: TypeAlias = str | int | float | bool | datetime | date | time | list["_TomlValue"] | dict[str, "_TomlValue"]


_MANIFEST_VERSION: Final[str] = "1.0"
_ROOT_KEYS: Final[frozenset[str]] = frozenset({"project", "dependency-groups", "tool"})
_PROJECT_KEYS: Final[frozenset[str]] = frozenset({"name", "version", "dependencies", "requires-python"})
_TOOL_TABLE_KEYS: Final[frozenset[str]] = frozenset({"pipx", "nab"})
_PIPX_KEYS: Final[frozenset[str]] = frozenset({"version", "tools"})
_TOOL_KEYS: Final[frozenset[str]] = frozenset({
    "suffix",
    "apps",
    "include-dependencies",
    "include-resources-from",
    "expose",
    "lock",
})


@dataclass(frozen=True)
class _FailedTool:
    environment: str
    error: str


@dataclass(frozen=True)
class ManifestData(OperationData):
    environments: tuple[str, ...]
    locks: tuple[str, ...]


__all__ = [
    "ManifestData",
    "lock_manifest",
    "sync_manifest",
]
