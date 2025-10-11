"""Clean command for pipx CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pipx.colors import bold, red
from pipx.constants import (
    EXIT_CODE_CACHE_CLEANUP_FAIL,
    EXIT_CODE_FULL_CLEANUP_FAIL,
    EXIT_CODE_LOGS_CLEANUP_FAIL,
    EXIT_CODE_OK,
    EXIT_CODE_TRASH_CLEANUP_FAIL,
    EXIT_CODE_VENVS_CLEANUP_FAIL,
    ExitCode,
)
from pipx.emojis import hazard, stars
from pipx.paths import ctx
from pipx.util import rmdir
from pipx.venv import VenvContainer

if TYPE_CHECKING:
    from pathlib import Path


def _cleanup_directory(
    path: Path,
    description: str,
    error_code: ExitCode,
    verbose: bool,
) -> ExitCode:
    """
    Remove a directory with standardized error handling and output.

    Args:
        path: Directory path to remove
        description: User-friendly description of what's being removed
        error_code: Exit code to return on failure
        verbose: Whether to print detailed output

    Returns:
        EXIT_CODE_OK on success, error_code on failure
    """
    if not path.exists():
        if verbose:
            print(f"Skipping {description} (directory doesn't exist)")
        return EXIT_CODE_OK

    action = f"Removing {description}..."
    if verbose:
        print(f"{action}")
        print(f"  Path: {path}")
    else:
        print(bold(action))

    try:
        rmdir(path, safe_rm=False)
    except Exception as e:
        print(f"{red(f'Error removing {description}:')} {e}")
        return error_code

    print(f"{stars} {description.capitalize()} removed.")
    return EXIT_CODE_OK


def _confirm_action(message: str) -> bool:
    """
    Prompt user for confirmation.

    Args:
        message: Question to ask the user

    Returns:
        True if user confirms, False otherwise
    """
    while True:
        response = input(f"{message} [y/N]: ").lower().strip()
        if response in ("y", "yes"):
            return True
        if response in ("n", "no", ""):
            return False
        print("Please answer 'y' or 'n'")


def _full_cleanup(verbose: bool) -> ExitCode:
    """
    Remove all pipx data, resetting to first installation state.

    This is the nuclear option - removes everything including:
    - All installed packages (venvs)
    - Cache and temporary data
    - Logs
    - Trash
    - Shared libraries

    Args:
        verbose: Print detailed output
        force: Skip confirmation prompt
    """
    print(f"{hazard}  {red('WARNING')}: This will remove ALL pipx data!")
    print(red("All installed packages will be lost."))
    print()

    return _cleanup_directory(
        path=ctx.home,
        description="all pipx data",
        error_code=EXIT_CODE_FULL_CLEANUP_FAIL,
        verbose=verbose,
    )


def _cache_cleanup(verbose: bool) -> ExitCode:
    """Remove cached virtual environments from 'pipx run' commands."""
    return _cleanup_directory(
        path=ctx.venv_cache,
        description="cache and temporary data",
        error_code=EXIT_CODE_CACHE_CLEANUP_FAIL,
        verbose=verbose,
    )


def _logs_cleanup(verbose: bool) -> ExitCode:
    """Remove pipx log files."""
    return _cleanup_directory(
        path=ctx.logs,
        description="logs",
        error_code=EXIT_CODE_LOGS_CLEANUP_FAIL,
        verbose=verbose,
    )


def _trash_cleanup(verbose: bool) -> ExitCode:
    """Remove files in the trash directory."""
    return _cleanup_directory(
        path=ctx.trash,
        description="trash",
        error_code=EXIT_CODE_TRASH_CLEANUP_FAIL,
        verbose=verbose,
    )


def _venvs_cleanup(verbose: bool) -> ExitCode:
    """Remove all installed packages and their virtual environments."""
    venv_container = VenvContainer(ctx.venvs)
    venv_dirs = list(venv_container.iter_venv_dirs())

    if not venv_dirs:
        if verbose:
            print("No installed packages to remove.")
        return EXIT_CODE_OK

    print(bold(f"Removing {len(venv_dirs)} installed package(s)..."))

    failed = []
    for venv_dir in venv_dirs:
        package_name = venv_dir.name
        try:
            if verbose:
                print(f"  Removing {package_name}...")
            rmdir(venv_dir, safe_rm=False)
        except Exception as e:
            failed.append((package_name, e))
            if verbose:
                print(f"    {red('Failed')}: {e}")

    if failed:
        print(f"{red(f'Failed to remove {len(failed)} package(s):')}")
        for package_name, error in failed:
            print(f"  - {package_name}: {error}")
        return EXIT_CODE_VENVS_CLEANUP_FAIL

    print(f"{stars} All installed packages removed.")
    return EXIT_CODE_OK


def clean(
    cache: bool = False,
    logs: bool = False,
    trash: bool = False,
    venvs: bool = False,
    verbose: bool = False,
    force: bool = False,
) -> ExitCode:
    """
    Clean pipx data directories.

    If no specific options are provided, performs a full cleanup removing
    all pipx data. Otherwise, removes only the specified components.

    Args:
        cache: Remove cache and temporary virtual environments
        logs: Remove log files
        trash: Empty trash directory
        venvs: Remove all installed packages
        verbose: Print detailed output including paths and progress

    Returns:
        Combined exit code (0 if all succeeded, non-zero if any failed)
    """
    if not force:
        if not _confirm_action("Are you sure you want to continue?"):
            print("Operation cancelled.")
            return EXIT_CODE_OK
    # Determine what to clean
    any_selected = cache or logs or trash or venvs

    if not any_selected:
        # No specific options: full cleanup
        return _full_cleanup(verbose)

    # Selective cleanup: run requested operations
    cleanup_operations = []
    if cache:
        cleanup_operations.append(_cache_cleanup)
    if logs:
        cleanup_operations.append(_logs_cleanup)
    if trash:
        cleanup_operations.append(_trash_cleanup)
    if venvs:
        cleanup_operations.append(_venvs_cleanup)

    # Execute all operations and combine exit codes
    for operation in cleanup_operations:
        result: ExitCode = operation(verbose)
        if result != EXIT_CODE_OK:
            return result

    return EXIT_CODE_OK
