from __future__ import annotations

import logging
import shlex
import site
import sys
from pathlib import Path
from typing import Final

import userpath  # type: ignore[import-not-found]

from pipx import paths
from pipx.constants import EXIT_CODE_OK, MACOS, ExitCode
from pipx.emojis import hazard, stars
from pipx.util import pipx_wrap

logger = logging.getLogger(__name__)

_GLOBAL_PATH_FILE: Final[Path] = Path("/etc/paths.d/pipx" if MACOS else "/etc/profile.d/pipx.sh")


def get_pipx_user_bin_path() -> Path | None:
    """Returns None if pipx is not installed using `pip --user`
    Otherwise returns parent dir of pipx binary
    """
    # NOTE: using this method to detect pip user-installed pipx will return
    #   None if pipx was installed as editable using `pip install --user -e`

    # https://docs.python.org/3/install/index.html#inst-alt-install-user
    #   Linux + Mac:
    #       scripts in <userbase>/bin
    #   Windows:
    #       scripts in <userbase>/Python<XY>/Scripts
    #       modules in <userbase>/Python<XY>/site-packages

    pipx_bin_path = None

    script_path = Path(__file__).resolve()
    userbase_path = Path(site.getuserbase()).resolve()
    try:
        _ = script_path.relative_to(userbase_path)
    except ValueError:
        pip_user_installed = False
    else:
        pip_user_installed = True
    if pip_user_installed:
        test_paths = (
            userbase_path / "bin" / "pipx",
            Path(site.getusersitepackages()).resolve().parent / "Scripts" / "pipx.exe",
        )
        for test_path in test_paths:
            if test_path.exists():
                pipx_bin_path = test_path.parent
                break

    return pipx_bin_path


def ensure_path(
    location: Path, *, force: bool, prepend: bool = False, all_shells: bool = False, dry_run: bool = False
) -> tuple[bool, bool]:
    """Ensure location is in user's PATH or add it to PATH.
    If prepend is True, location will be prepended to PATH, else appended.
    If dry_run is True, report what would change without modifying PATH or
    any shell configuration file.
    Returns True if location was added to PATH
    """
    location_str = str(location)
    path_added = False
    need_shell_restart = userpath.need_shell_restart(location_str)
    in_current_path = userpath.in_current_path(location_str)

    if force or (not in_current_path and not need_shell_restart):
        if dry_run:
            action = "prepend" if prepend else "append"
            print(  # ruff:ignore[print]  # user-facing CLI output
                pipx_wrap(
                    f"Would {action} {location_str} to the PATH environment variable.",
                    subsequent_indent=" " * 4,
                )
            )
            return (False, False)
        if prepend:
            path_added = userpath.prepend(location_str, "pipx", all_shells=all_shells)
        else:
            path_added = userpath.append(location_str, "pipx", all_shells=all_shells)
        if not path_added:
            print(  # ruff:ignore[print]  # user-facing CLI output
                pipx_wrap(
                    f"{hazard}  {location_str} is not added to the PATH environment variable successfully. "
                    f"You may need to add it to PATH manually.",
                    subsequent_indent=" " * 4,
                )
            )
        else:
            print(  # ruff:ignore[print]  # user-facing CLI output
                pipx_wrap(
                    f"Success! Added {location_str} to the PATH environment variable.",
                    subsequent_indent=" " * 4,
                )
            )
        need_shell_restart = userpath.need_shell_restart(location_str)
    elif not in_current_path and need_shell_restart:
        print(  # ruff:ignore[print]  # user-facing CLI output
            pipx_wrap(
                f"""
                {location_str} has been added to PATH, but you need to
                open a new terminal or re-login for this PATH change to take
                effect. Alternatively, you can source your shell's config file
                with e.g. 'source ~/.bashrc'.
                """,
                subsequent_indent=" " * 4,
            )
        )
    else:
        print(  # ruff:ignore[print]  # user-facing CLI output
            pipx_wrap(f"{location_str} is already in PATH.", subsequent_indent=" " * 4)
        )

    return (path_added, need_shell_restart)


def _ensure_global_path(location: Path, *, force: bool, prepend: bool, dry_run: bool) -> bool:
    config_file = _GLOBAL_PATH_FILE
    if MACOS:
        contents = f"{location}\n"
    else:
        quoted_location = shlex.quote(str(location))
        assignment = f'export PATH={quoted_location}:"$PATH"' if prepend else f'export PATH="$PATH":{quoted_location}'
        contents = f'case ":$PATH:" in *:{quoted_location}:*) ;; *) {assignment} ;; esac\n'

    if not force and config_file.exists() and config_file.read_text(encoding="utf-8") == contents:
        print(  # ruff:ignore[print]  # user-facing CLI output
            pipx_wrap(f"{location} is already in the system PATH configuration.", subsequent_indent=" " * 4)
        )
        return False

    if dry_run:
        print(  # ruff:ignore[print]  # user-facing CLI output
            pipx_wrap(
                f"Would write {location} to the system PATH configuration at {config_file}.",
                subsequent_indent=" " * 4,
            )
        )
        return False

    config_file.write_text(contents, encoding="utf-8")
    config_file.chmod(0o644)
    print(  # ruff:ignore[print]  # user-facing CLI output
        pipx_wrap(
            f"Success! Added {location} to the system PATH configuration at {config_file}.",
            subsequent_indent=" " * 4,
        )
    )
    return True


def ensure_pipx_paths(
    *,
    force: bool,
    prepend: bool = False,
    all_shells: bool = False,
    dry_run: bool = False,
    is_global: bool = False,
) -> ExitCode:
    """Returns pipx exit code."""
    if is_global:
        path_added = _ensure_global_path(paths.ctx.bin_dir, force=force, prepend=prepend, dry_run=dry_run)
        print()  # ruff:ignore[print]  # user-facing CLI output

        if dry_run:
            print(  # ruff:ignore[print]  # user-facing CLI output
                pipx_wrap("This was a dry run; no changes were made to the system PATH configuration.")
            )
        elif path_added:
            print(  # ruff:ignore[print]  # user-facing CLI output
                pipx_wrap("Users must open a new terminal or re-login for the PATH change to take effect.") + "\n"
            )

        print(f"Otherwise pipx is ready to go! {stars}")  # ruff:ignore[print]  # user-facing CLI output
        return EXIT_CODE_OK

    bin_paths = {paths.ctx.bin_dir}

    pipx_user_bin_path = get_pipx_user_bin_path()
    if pipx_user_bin_path is not None:
        bin_paths.add(pipx_user_bin_path)

    path_added = False
    need_shell_restart = False
    path_action_str = "prepended to" if prepend else "appended to"

    for bin_path in bin_paths:
        (path_added_current, need_shell_restart_current) = ensure_path(
            bin_path, prepend=prepend, force=force, all_shells=all_shells, dry_run=dry_run
        )
        path_added |= path_added_current
        need_shell_restart |= need_shell_restart_current

    print()  # ruff:ignore[print]  # user-facing CLI output

    if dry_run:
        print(  # ruff:ignore[print]  # user-facing CLI output
            pipx_wrap("This was a dry run; no changes were made to your PATH or shell configuration files.")
        )
        return EXIT_CODE_OK

    if path_added:
        print(  # ruff:ignore[print]  # user-facing CLI output
            pipx_wrap(
                """
                Consider adding shell completions for pipx. Run 'pipx
                completions' for instructions.
                """
            )
            + "\n"
        )
    elif not need_shell_restart:
        sys.stdout.flush()
        no_change_warning = (
            pipx_wrap(
                f"""
                {hazard}  All pipx binary directories have been {path_action_str} PATH. If you
                are sure you want to proceed, try again with the '--force'
                flag.
                """
            )
            + "\n"
        )
        logger.warning(no_change_warning)

    if need_shell_restart:
        print(  # ruff:ignore[print]  # user-facing CLI output
            pipx_wrap(
                """
                You will need to open a new terminal or re-login for the PATH
                changes to take effect. Alternatively, you can source your shell's
                config file with e.g. 'source ~/.bashrc'.
                """
            )
            + "\n"
        )

    print(f"Otherwise pipx is ready to go! {stars}")  # ruff:ignore[print]  # user-facing CLI output

    return EXIT_CODE_OK
