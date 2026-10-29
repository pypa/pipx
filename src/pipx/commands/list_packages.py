from __future__ import annotations

__lazy_modules__ = [
    "json",
    "pipx",
    "pipx.commands.common",
    "pipx.commands.transaction",
    "pipx.pipx_metadata_file",
    "pipx.self_install",
    "pipx.venv",
]

import json
import logging
import sys
from typing import TYPE_CHECKING, Final

from pipx import paths
from pipx.colors import BOLD
from pipx.commands.common import VenvProblems, get_venv_summary, reuse_resource_dir_scans, venv_health_check
from pipx.commands.transaction import is_unfinished
from pipx.constants import EXIT_CODE_LIST_PROBLEM, EXIT_CODE_OK, WINDOWS, ExitCode
from pipx.emojis import SLEEP
from pipx.pipx_metadata_file import JsonEncoderHandlesPath, PipxMetadata
from pipx.self_install import backs_self_managed_venv
from pipx.venv import Venv, VenvContainer

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable
    from pathlib import Path

    from pipx.options import ListOptions

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


def list_packages(venv_container: VenvContainer, venv_dirs: Collection[Path], options: ListOptions) -> ExitCode:
    if not venv_dirs:
        print(  # ruff:ignore[print]  # user-facing CLI output
            f"nothing has been installed with pipx {SLEEP}", file=sys.stderr
        )

    locked_venv_dirs: Final = venv_container.iter_locked_venv_dirs(venv_dirs, allow_permission_error=True)
    if options.json_format:
        all_venv_problems = _list_json(locked_venv_dirs)
    elif options.short_format:
        all_venv_problems = _list_short(locked_venv_dirs)
    elif options.pinned_only:
        all_venv_problems = _list_pinned(locked_venv_dirs, include_injected=options.include_injected)
    else:
        if not venv_dirs:
            return EXIT_CODE_OK
        all_venv_problems = _list_text(locked_venv_dirs, str(venv_container), include_injected=options.include_injected)

    _log_venv_problems(all_venv_problems)

    if unfinished := [venv_dir.name for venv_dir in venv_dirs if is_unfinished(venv_dir)]:
        _LOGGER.warning(
            "\nOne or more packages were left half changed by an interrupted pipx run: %s.\n"
            "   To fix, execute: pipx upgrade-all, or pipx reinstall PACKAGE",
            ", ".join(unfinished),
        )

    if all_venv_problems.any_() or unfinished:
        print(file=sys.stderr)  # ruff:ignore[print]  # user-facing CLI output
        return EXIT_CODE_LIST_PROBLEM

    return EXIT_CODE_OK


def _list_json(venv_dirs: Iterable[Path]) -> VenvProblems:
    warning_messages: Final[list[str]] = []
    listed: Final[dict[str, PipxMetadata]] = {}
    all_venv_problems = VenvProblems()
    for venv_dir in venv_dirs:
        venv_metadata, venv_problems, warning_message = _venv_metadata_summary(venv_dir)
        all_venv_problems = all_venv_problems.or_(venv_problems)
        if venv_problems.any_():
            warning_messages.append(warning_message)
            continue
        if _records_stale_self_managed_python(venv_metadata):
            # install-all would build on whatever interpreter appears at the recorded path again
            venv_metadata.source_interpreter = None
        listed[venv_dir.name] = venv_metadata

    print(  # ruff:ignore[print]  # user-facing CLI output
        json.dumps(
            {
                "pipx_spec_version": "0.1",
                "venvs": {name: {"metadata": venv_metadata.to_dict()} for name, venv_metadata in listed.items()},
            },
            indent=4,
            sort_keys=True,
            cls=JsonEncoderHandlesPath,
        )
    )
    for warning_message in warning_messages:
        _LOGGER.warning(warning_message)

    return all_venv_problems


def _records_stale_self_managed_python(venv_metadata: PipxMetadata) -> bool:
    # pipx is self-managed only on POSIX, where its venv links bin/python to the interpreter it is built on
    return (
        not WINDOWS
        and venv_metadata.main_package.package == "pipx"
        and (recorded := venv_metadata.source_interpreter) is not None
        and not backs_self_managed_venv(recorded, venv_metadata.venv_dir)
    )


def _venv_metadata_summary(venv_dir: Path) -> tuple[PipxMetadata, VenvProblems, str]:
    venv: Final[Venv] = Venv(venv_dir)
    venv_problems, warning_message = venv_health_check(venv)
    if venv_problems.any_():
        return PipxMetadata(venv_dir, read=False), venv_problems, warning_message
    return venv.pipx_metadata, venv_problems, ""


def _list_short(venv_dirs: Iterable[Path]) -> VenvProblems:
    all_venv_problems = VenvProblems()
    for venv_dir in venv_dirs:
        venv_metadata, venv_problems, warning_message = _venv_metadata_summary(venv_dir)
        if venv_problems.any_():
            _LOGGER.warning(warning_message)
        else:
            print(  # ruff:ignore[print]  # user-facing CLI output
                venv_metadata.main_package.package,
                venv_metadata.main_package.package_version,
            )
        all_venv_problems = all_venv_problems.or_(venv_problems)

    return all_venv_problems


def _list_pinned(venv_dirs: Iterable[Path], *, include_injected: bool) -> VenvProblems:
    all_venv_problems = VenvProblems()
    for venv_dir in venv_dirs:
        venv_metadata, venv_problems, warning_message = _venv_metadata_summary(venv_dir)
        if venv_problems.any_():
            _LOGGER.warning(warning_message)
        else:
            if venv_metadata.main_package.pinned:
                print(  # ruff:ignore[print]  # user-facing CLI output
                    venv_metadata.main_package.package,
                    venv_metadata.main_package.package_version,
                )
            if include_injected:
                for package_name, package in venv_metadata.injected_packages.items():
                    if package.pinned:
                        print(  # ruff:ignore[print]  # user-facing CLI output
                            package_name, package.package_version, f"(injected in venv {venv_dir.name})"
                        )
        all_venv_problems = all_venv_problems.or_(venv_problems)

    return all_venv_problems


def _list_text(venv_dirs: Iterable[Path], venv_root_dir: str, *, include_injected: bool) -> VenvProblems:
    print(f"venvs are in {BOLD(venv_root_dir)}")  # ruff:ignore[print]  # user-facing CLI output
    print(  # ruff:ignore[print]  # user-facing CLI output
        f"apps are exposed on your $PATH at {BOLD(str(paths.CTX.bin_dir))}"
    )
    print(f"manual pages are exposed at {BOLD(str(paths.CTX.man_dir))}")  # ruff:ignore[print]  # user-facing CLI output
    print(  # ruff:ignore[print]  # user-facing CLI output
        f"shell completions are exposed at {BOLD(str(paths.CTX.completion_dir))}"
    )

    all_venv_problems = VenvProblems()
    with reuse_resource_dir_scans():
        for venv_dir in venv_dirs:
            package_summary, venv_problems = get_venv_summary(venv_dir, include_injected=include_injected)
            if venv_problems.any_():
                _LOGGER.warning(package_summary)
            else:
                print(package_summary)  # ruff:ignore[print]  # user-facing CLI output
            all_venv_problems = all_venv_problems.or_(venv_problems)

    return all_venv_problems


def _log_venv_problems(problems: VenvProblems) -> None:
    if problems.bad_venv_name:
        _LOGGER.warning(
            "\nOne or more packages contain out-of-date internal data installed from a\n"
            "previous pipx version and need to be updated.\n"
            "    To fix, execute: pipx reinstall-all"
        )
    if problems.invalid_interpreter:
        _LOGGER.warning(
            "\nOne or more packages have a missing python interpreter.\n    To fix, execute: pipx reinstall-all"
        )
    if problems.missing_metadata:
        _LOGGER.warning(
            "\nOne or more packages have no internal pipx metadata.\n"
            "   pipx versions before 0.15.0.0 did not record it.\n"
            "   Uninstall and install these packages to fix them."
        )
    if problems.unreadable_metadata:
        _LOGGER.warning(
            "\nOne or more packages have internal pipx metadata this user cannot read.\n"
            "   pipx keeps it readable by its owner only, since it can hold index credentials.\n"
            "   Run the command as that user, for example with sudo for --global, to list them."
        )
    if problems.not_installed:
        _LOGGER.warning(
            "\nOne or more packages are not installed properly.\n   Uninstall and install these packages to fix them."
        )


__all__ = [
    "list_packages",
]
