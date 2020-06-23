import logging
from pathlib import Path
import site
from typing import Tuple

import userpath  # type: ignore
from pipx.emojies import stars
from pipx import constants


def ensure_path(location: Path, *, force: bool) -> Tuple[bool, bool]:
    """Ensure location is in user's PATH or add it to PATH.
    Returns True if location was added to PATH
    """
    location_str = str(location)
    path_appended = False
    need_shell_restart = userpath.need_shell_restart(location_str)
    in_current_path = userpath.in_current_path(location_str)

    if force or not in_current_path:
        userpath.append(location_str)
        print(f"Success! Added {location_str} to the PATH environment variable.")
        path_appended = True
        need_shell_restart = userpath.need_shell_restart(location_str)
    else:
        # not force and in_current_path
        if need_shell_restart:
            logging.warning(
                (
                    f"The directory `{location_str}` is already in PATH.\n"
                    "    If you are sure you want add it again, try again with "
                    "the '--force' flag."
                )
            )
        else:
            print(f"{location_str} has been already been added to PATH. ")

    return (path_appended, need_shell_restart)


def ensure_pipx_paths(force: bool):
    # NOTE: using this method to detect pip user-installed pipx will return
    #   False if pipx was installed as editable using `pip install -e`
    script_path = Path(__file__).resolve()
    pip_user_path = Path(site.getuserbase()).resolve()
    try:
        _ = script_path.relative_to(pip_user_path)
    except ValueError:
        pip_user_installed = False
    else:
        pip_user_installed = True

    (path_added1, need_shell_restart1) = ensure_path(
        constants.LOCAL_BIN_DIR, force=force
    )
    if pip_user_installed and (pip_user_path / "bin").exists():
        (path_added2, need_shell_restart2) = ensure_path(
            pip_user_path / "bin", force=force
        )
    else:
        (path_added2, need_shell_restart2) = (False, False)

    if path_added1 or path_added2:
        print(
            "\nConsider adding shell completions for pipx.\n"
            "Run 'pipx completions' for instructions."
        )

    if need_shell_restart1 or need_shell_restart2:
        print(
            "\nYou likely need to open a new terminal or re-login for "
            "the changes to take\neffect."
        )

    print(f"\nOtherwise pipx is ready to go! {stars}")
