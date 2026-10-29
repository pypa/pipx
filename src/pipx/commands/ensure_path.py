from __future__ import annotations

__lazy_modules__ = ["pipx", "pipx.util", "pipx.wrap", "re", "shlex", "typing", "userpath"]

import logging
import re
import shlex
import site
import sys
from pathlib import Path
from typing import Final

import userpath

from pipx import paths
from pipx.constants import EXIT_CODE_OK, MACOS, ExitCode
from pipx.emojis import HAZARD, STARS
from pipx.util import PipxError
from pipx.wrap import pipx_wrap

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

_GLOBAL_PATH_FILE: Final[Path] = Path("/etc/paths.d/pipx" if MACOS else "/etc/profile.d/pipx.sh")


def ensure_pipx_paths(*, force: bool, prepend: bool, all_shells: bool, dry_run: bool, is_global: bool) -> ExitCode:
    if is_global:
        written: Final[bool] = _ensure_global_path(paths.CTX.bin_dir, force=force, prepend=prepend, dry_run=dry_run)
        print()  # ruff:ignore[print]  # user-facing CLI output

        if dry_run:
            print(  # ruff:ignore[print]  # user-facing CLI output
                pipx_wrap("This was a dry run; no changes were made to the system PATH configuration.")
            )
        elif written:
            print(  # ruff:ignore[print]  # user-facing CLI output
                pipx_wrap("Users must open a new terminal or re-login for the PATH change to take effect.") + "\n"
            )

        print(f"Otherwise pipx is ready to go! {STARS}")  # ruff:ignore[print]  # user-facing CLI output
        return EXIT_CODE_OK

    bin_paths: Final[set[Path]] = {paths.CTX.bin_dir}
    if (pipx_user_bin_path := _get_pipx_user_bin_path()) is not None:
        bin_paths.add(pipx_user_bin_path)

    outcomes: Final[list[tuple[bool, bool]]] = [
        ensure_path(bin_path, prepend=prepend, force=force, all_shells=all_shells, dry_run=dry_run)
        for bin_path in bin_paths
    ]
    path_added: Final[bool] = any(added for added, _ in outcomes)
    need_shell_restart: Final[bool] = any(restart for _, restart in outcomes)

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
        path_action_str: Final[str] = "prepended to" if prepend else "appended to"
        _LOGGER.warning(
            "%s\n",
            pipx_wrap(
                f"""
                {HAZARD}  All pipx binary directories have been {path_action_str} PATH. If you
                are sure you want to proceed, try again with the '--force'
                flag.
                """
            ),
        )

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

    print(f"Otherwise pipx is ready to go! {STARS}")  # ruff:ignore[print]  # user-facing CLI output

    return EXIT_CODE_OK


def _ensure_global_path(location: Path, *, force: bool, prepend: bool, dry_run: bool) -> bool:
    if MACOS:
        contents = f"{location}\n"
    else:
        quoted_location = shlex.quote(str(location))
        assignment = f'export PATH={quoted_location}:"$PATH"' if prepend else f'export PATH="$PATH":{quoted_location}'
        contents = f'case ":$PATH:" in *:{quoted_location}:*) ;; *) {assignment} ;; esac\n'

    if not force:
        try:
            existing = _GLOBAL_PATH_FILE.read_text(encoding="utf-8") if _GLOBAL_PATH_FILE.exists() else ""
        except UnicodeDecodeError:  # pipx writes UTF-8, so undecodable bytes came from someone else
            existing = None
        if existing == contents:
            print(  # ruff:ignore[print]  # user-facing CLI output
                pipx_wrap(f"{location} is already in the system PATH configuration.", subsequent_indent=" " * 4)
            )
            return False
        # the name alone does not make the file pipx's: an administrator may keep other settings in it
        if existing is None or (existing and not _written_by_pipx(existing)):
            msg = (
                f"{_GLOBAL_PATH_FILE} holds content pipx did not write, so pipx left it alone. Add {location} to PATH "
                "there yourself, or pass --force to replace the file."
            )
            raise PipxError(msg)

    if dry_run:
        print(  # ruff:ignore[print]  # user-facing CLI output
            pipx_wrap(
                f"Would write {location} to the system PATH configuration at {_GLOBAL_PATH_FILE}.",
                subsequent_indent=" " * 4,
            )
        )
        return False

    _GLOBAL_PATH_FILE.write_text(contents, encoding="utf-8")
    _GLOBAL_PATH_FILE.chmod(0o644)
    print(  # ruff:ignore[print]  # user-facing CLI output
        pipx_wrap(
            f"Success! Added {location} to the system PATH configuration at {_GLOBAL_PATH_FILE}.",
            subsequent_indent=" " * 4,
        )
    )
    return True


def _written_by_pipx(contents: str) -> bool:
    if MACOS:  # /etc/paths.d holds one directory per line, so only a single line can be pipx's own entry
        return len(contents.splitlines()) == 1
    # the entry an earlier run wrote for any location, appended or prepended
    entry: Final[str] = (
        r'case ":\$PATH:" in \*:(?P<location>.+?):\*\) ;; \*\) '
        r'export PATH=(?:(?P=location):"\$PATH"|"\$PATH":(?P=location)) ;; esac\n'
    )
    return re.fullmatch(entry, contents) is not None


def _get_pipx_user_bin_path() -> Path | None:
    # misses a pipx installed as editable with `pip install --user -e`
    userbase_path: Final[Path] = Path(site.getuserbase()).resolve()
    if not Path(__file__).resolve().is_relative_to(userbase_path):
        return None
    # the user scheme puts scripts in <userbase>/bin on Linux and macOS, and in <userbase>/Python<XY>/Scripts on
    # Windows: https://docs.python.org/3/library/sysconfig.html#user-scheme
    return next(
        (
            script.parent
            for script in (
                userbase_path / "bin" / "pipx",
                Path(site.getusersitepackages()).resolve().parent / "Scripts" / "pipx.exe",
            )
            if script.exists()
        ),
        None,
    )


def ensure_path(location: Path, *, force: bool, prepend: bool, all_shells: bool, dry_run: bool) -> tuple[bool, bool]:
    location_str: Final[str] = str(location)
    need_shell_restart: Final[bool] = userpath.need_shell_restart(location_str)
    in_current_path: Final[bool] = userpath.in_current_path(location_str)

    if force or (not in_current_path and not need_shell_restart):
        if dry_run:
            print(  # ruff:ignore[print]  # user-facing CLI output
                pipx_wrap(
                    f"Would {'prepend' if prepend else 'append'} {location_str} to the PATH environment variable.",
                    subsequent_indent=" " * 4,
                )
            )
            return False, False
        path_added: Final[bool] = (userpath.prepend if prepend else userpath.append)(
            location_str, "pipx", all_shells=all_shells
        )
        if path_added:
            print(  # ruff:ignore[print]  # user-facing CLI output
                pipx_wrap(
                    f"Success! Added {location_str} to the PATH environment variable.",
                    subsequent_indent=" " * 4,
                )
            )
        else:
            print(  # ruff:ignore[print]  # user-facing CLI output
                pipx_wrap(
                    f"{HAZARD}  {location_str} is not added to the PATH environment variable successfully. "
                    f"You may need to add it to PATH manually.",
                    subsequent_indent=" " * 4,
                )
            )
        return path_added, userpath.need_shell_restart(location_str)
    if not in_current_path and need_shell_restart:
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
    return False, need_shell_restart


__all__ = [
    "ensure_path",
    "ensure_pipx_paths",
]
