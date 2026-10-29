from __future__ import annotations

__lazy_modules__ = [
    "collections",
    "contextlib",
    "packaging.requirements",
    "packaging.utils",
    "pathlib",
    "pipx.commands.common",
    "pipx.commands.expose",
    "pipx.commands.install",
    "pipx.commands.uninstall",
    "pipx.options",
    "pipx.package_specifier",
    "pipx.pipx_metadata_file",
    "pipx.redact",
    "pipx.util",
    "shutil",
    "subprocess",
    "tempfile",
    "tomllib",
]

import subprocess
import tomllib
from collections import Counter
from contextlib import suppress
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from shutil import copy2, which
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Final, TypeAlias

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from pipx.commands.common import force_replaces_only
from pipx.commands.expose import expose, unexpose
from pipx.commands.install import install
from pipx.commands.uninstall import uninstall
from pipx.constants import EXIT_CODE_OK, ExitCode
from pipx.options import ExposureOptions, InstallOptions
from pipx.package_specifier import trusted_recorded_pip_args
from pipx.pipx_metadata_file import PipxMetadata
from pipx.redact import redact_url_credentials
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
    from typing import TypeIs

    from pipx.options import SyncOptions
    from pipx.venv import VenvContainer


def sync_manifest(
    manifest_file: Path, venv_container: VenvContainer, options: SyncOptions
) -> OperationResult[ManifestData]:
    manifest: Final[_Manifest] = _load_manifest(manifest_file, require_locks=True)
    failures: Final[list[_FailedTool]] = []
    messages: Final[list[OutputMessage]] = []
    synced: Final[list[str]] = []
    for tool in manifest.tools:
        venv_dir: Final[Path] = venv_container.get_venv_dir(tool.environment)
        with venv_container.venv_lock(venv_dir) as venv_lock:
            existed: Final[bool] = venv_dir.is_dir()
            recorded: Final[PipxMetadata] = PipxMetadata(venv_dir)
            was_exposed: Final[bool] = existed and recorded.exposure_enabled
            try:
                if was_exposed:
                    unexpose(venv_dir, options.local_bin_dir, options.local_man_dir, verbose=options.verbose)
                # unexpose already removed what the environment held, so nothing else is the rebuild's to replace
                with force_replaces_only(()):
                    outcome: Final = install(
                        venv_dir,
                        [tool.package_name],
                        [tool.package],
                        InstallOptions(
                            local_bin_dir=options.local_bin_dir,
                            local_man_dir=options.local_man_dir,
                            python=options.python,
                            pip_args=trusted_recorded_pip_args(recorded.main_package.pip_args, venv_dir),
                            venv_args=recorded.venv_args,
                            verbose=options.verbose,
                            force=existed,
                            reinstall=False,
                            exposure=ExposureOptions(
                                include_dependencies=tool.include_dependencies,
                                include_resources_from=tool.include_resources_from,
                                suffix=tool.suffix,
                            ),
                            preinstall_packages=None,
                            expected_apps=tool.apps,
                            lock_file=tool.lock_file,
                            backend=options.backend,
                            exposure_enabled=tool.expose,
                            preserve_existing=True,
                            replace_expected_apps=True,
                            replace_lock=True,
                            emit_output=False,
                        ),
                        venv_lock=venv_lock,
                    )
                error_message = outcome.errors[0].message if outcome.errors else None
            except PipxError as error:
                error_message = str(error)
            except (Exception, KeyboardInterrupt):
                # install rolls the environment back on an interrupt or a crash too, to the copy taken after unexpose
                if was_exposed:
                    expose(venv_dir, options.local_bin_dir, options.local_man_dir, verbose=options.verbose)
                raise
            # install returns a failed result rather than raising when it does not render, so check both
            if error_message is not None:
                failures.append(_FailedTool(environment=tool.environment, error=error_message))
                messages.append(OutputMessage(text=error_message, stream=OutputStream.STDERR, level=OutputLevel.ERROR))
                if was_exposed:
                    expose(venv_dir, options.local_bin_dir, options.local_man_dir, verbose=options.verbose)
            else:
                synced.append(tool.environment)
                # install links the main package alone, while unexpose also dropped the links of injected packages
                if existed and tool.expose:
                    expose(venv_dir, options.local_bin_dir, options.local_man_dir, verbose=options.verbose)

    if options.prune and not failures:
        messages.extend(
            _prune_environments(
                manifest, venv_container, options.local_bin_dir, options.local_man_dir, verbose=options.verbose
            )
        )
    return OperationResult(
        command=("manifest", "sync"),
        data=ManifestData(environments=tuple(synced), locks=()),
        messages=tuple(messages),
        exit_code=ExitCode(1) if failures else EXIT_CODE_OK,
        errors=tuple(
            OperationError(code="manifest_sync_failed", message=failure.error, environment=failure.environment)
            for failure in failures
        ),
        succeeded=bool(synced),
    )


def _load_manifest(manifest_file: Path, *, require_locks: bool) -> _Manifest:
    path: Final[Path] = manifest_file.expanduser().resolve()
    try:
        with path.open("rb") as file:
            data: Final[dict[str, _TomlValue]] = tomllib.load(file)
    except FileNotFoundError as error:
        msg = f"Manifest does not exist: {path}"
        raise PipxError(msg) from error
    except (OSError, tomllib.TOMLDecodeError) as error:
        msg = f"Cannot read manifest {path}: {error}"
        raise PipxError(msg) from error

    groups, tool_data = _parse_manifest_tables(data)

    tools: Final[list[_ManifestTool]] = []
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
    if unknown := sorted(set(data) - {"project", "dependency-groups", "tool"}):
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
    if unknown := sorted(set(tool_table) - {"pipx", "nab"}):
        msg = f"Unknown manifest tool {'table' if len(unknown) == 1 else 'tables'}: {', '.join(unknown)}"
        raise PipxError(msg)
    if (nab_data := tool_table.get("nab")) is not None and not isinstance(nab_data, dict):
        msg = "Manifest tool.nab must be a table."
        raise PipxError(msg)
    return groups, _parse_pipx_table(tool_table, groups)


def _validate_project(data: dict[str, _TomlValue]) -> None:
    if unknown := sorted(set(data) - {"name", "version", "dependencies", "requires-python"}):
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
    if unknown := sorted(set(pipx_data) - {"version", "tools"}):
        msg = f"Unknown tool.pipx {'key' if len(unknown) == 1 else 'keys'}: {', '.join(unknown)}"
        raise PipxError(msg)
    manifest_version: Final[str] = "1.0"
    if pipx_data.get("version") != manifest_version:
        msg = f'Manifest version must be "{manifest_version}".'
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
    if unknown := sorted(
        set(data) - {"suffix", "apps", "include-dependencies", "include-resources-from", "expose", "lock"}
    ):
        msg = f"Unknown {'key' if len(unknown) == 1 else 'keys'} for manifest tool {environment}: {', '.join(unknown)}"
        raise PipxError(msg)
    package_name: Final[str] = _parse_package(environment, package)
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
        requirement: Final[Requirement] = Requirement(package)
    except InvalidRequirement:
        msg = f"Manifest tool {environment} has an invalid package requirement: {redact_url_credentials(package)}"
        # packaging quotes the requirement in its message, so chaining it would log the credentials with the traceback
        raise PipxError(msg) from None
    if requirement.marker is not None:
        msg = f"Manifest tool {environment} cannot use an environment marker."
        raise PipxError(msg)
    return canonicalize_name(requirement.name)


def _parse_include_resources_from(environment: str, data: dict[str, _TomlValue]) -> tuple[str, ...]:
    if not _is_non_empty_strings(packages := data.get("include-resources-from", [])):
        msg = f"Manifest tool {environment} include-resources-from must be non-empty strings."
        raise PipxError(msg)
    included: Final[tuple[str, ...]] = tuple(canonicalize_name(package) for package in packages)
    if len(included) != len(set(included)):
        msg = f"Manifest tool {environment} include-resources-from must be unique."
        raise PipxError(msg)
    return included


def _is_non_empty_strings(value: object) -> TypeIs[list[str]]:
    return isinstance(value, list) and all(isinstance(item, str) and item for item in value)


def _parse_apps(environment: str, data: dict[str, _TomlValue]) -> tuple[str, ...]:
    if not _is_non_empty_strings(apps := data.get("apps", [])):
        msg = f"Manifest tool {environment} apps must be non-empty strings."
        raise PipxError(msg)
    if len(apps) != len(set(apps)):
        msg = f"Manifest tool {environment} apps must be unique."
        raise PipxError(msg)
    return tuple(apps)


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
    # joining onto the manifest directory keeps an absolute lock path as it is
    lock_file: Final[Path] = (manifest_dir / Path(lock_value).expanduser()).resolve()
    if not _is_pylock_name(lock_file.name):
        msg = f"Manifest tool {environment} lock must be named pylock.toml or pylock.<name>.toml."
        raise PipxError(msg)
    if require_locks and not lock_file.is_file():
        msg = f"Lock file does not exist for manifest tool {environment}: {lock_file}"
        raise PipxError(msg)
    return lock_file


def _is_pylock_name(name: str) -> bool:
    if name == "pylock.toml":
        return True
    return (
        name.startswith("pylock.")
        and name.endswith(".toml")
        and bool(lock_name := name.removeprefix("pylock.").removesuffix(".toml"))
        and "." not in lock_name
    )


@dataclass(frozen=True, slots=True, kw_only=True)
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


def _duplicate_lock_files(tools: list[_ManifestTool]) -> tuple[Path, ...]:
    counts: Final[Counter[Path]] = Counter(tool.lock_file for tool in tools if tool.lock_file is not None)
    return tuple(sorted(lock_file for lock_file, count in counts.items() if count > 1))


@dataclass(frozen=True, slots=True, kw_only=True)
class _Manifest:
    path: Path
    tools: tuple[_ManifestTool, ...]


_TomlValue: TypeAlias = str | int | float | bool | datetime | date | time | list["_TomlValue"] | dict[str, "_TomlValue"]


@dataclass(frozen=True, slots=True, kw_only=True)
class _FailedTool:
    environment: str
    error: str


def _prune_environments(
    manifest: _Manifest,
    venv_container: VenvContainer,
    local_bin_dir: Path,
    local_man_dir: Path,
    *,
    verbose: bool,
) -> list[OutputMessage]:
    declared: Final[set[str]] = {tool.environment for tool in manifest.tools}
    messages: Final[list[OutputMessage]] = []
    for venv_dir in sorted(venv_container.iter_venv_dirs()):
        if venv_dir.name in declared:
            continue
        with venv_container.venv_lock(venv_dir):
            messages.extend(uninstall(venv_dir, local_bin_dir, local_man_dir, verbose=verbose).messages)
    return messages


@dataclass(frozen=True, slots=True, kw_only=True)
class ManifestData(OperationData):
    environments: tuple[str, ...]
    locks: tuple[str, ...]


def lock_manifest(manifest_file: Path) -> OperationResult[ManifestData]:
    manifest: Final[_Manifest] = _load_manifest(manifest_file, require_locks=False)
    if not any(tool.lock_file is not None for tool in manifest.tools):
        msg = "The manifest does not declare any lock files."
        raise PipxError(msg)
    if outside := sorted(
        str(tool.lock_file)
        for tool in manifest.tools
        if tool.lock_file is not None and not tool.lock_file.is_relative_to(manifest.path.parent)
    ):
        msg = f"Manifest lock files must be inside the manifest directory {manifest.path.parent}: {', '.join(outside)}"
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
        messages=tuple(OutputMessage(text=f"locked {lock_file}") for lock_file in locked),
    )


def _generate_locks(manifest: _Manifest, nab: str) -> list[str]:
    with TemporaryDirectory(prefix=".pipx-lock-", dir=manifest.path.parent) as temporary_dir:
        generated: Final[list[tuple[Path, Path]]] = []
        for tool in manifest.tools:
            if tool.lock_file is None:
                continue
            tool_dir: Final[Path] = Path(temporary_dir) / tool.environment
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
                    # nab marks every group member with `"<group>" in dependency_groups`, and an installer selects
                    # no groups unless the lock names one as its default, so without this the lock installs nothing
                    "--project-default-group",
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

        backups_dir: Final[Path] = Path(temporary_dir) / ".previous"
        backups_dir.mkdir()
        locked: Final[list[str]] = []
        # replacing the whole set one file at a time is not atomic, so back each target up first and, if any replacement
        # fails, roll every applied one back to leave the manifest's locks all-old rather than half-new
        applied: Final[list[tuple[Path, Path | None]]] = []
        try:  # ruff:ignore[too-many-statements-in-try-clause]  # one handler rolls back every applied lock
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
                # what broke a swap-in (a directory at the lock path) can break its undo too, and the backups go away
                # with the temporary directory, so one failed undo must not keep the earlier locks from being restored
                with suppress(OSError):
                    if backup is not None:
                        backup.replace(lock_file)
                    else:
                        lock_file.unlink(missing_ok=True)
            raise
    return locked


__all__ = [
    "ManifestData",
    "lock_manifest",
    "sync_manifest",
]
