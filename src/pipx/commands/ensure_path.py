import logging
from pathlib import Path
import site
from typing import Tuple, Optional

import userpath  # type: ignore
from pipx.emojies import stars
from pipx import constants


def get_pipx_user_bin_path() -> Optional[Path]:
    """Returns None if pipx is not installed using `pip --user`
    Otherwise returns parent dir of pipx binary
    """
    # NOTE: using this method to detect pip user-installed pipx will return
    #   None if pipx was installed as editable using `pip install --user -e`
    script_path = Path(__file__).resolve()
    pip_user_path = Path(site.getuserbase()).resolve()
    try:
        _ = script_path.relative_to(pip_user_path)
    except ValueError:
        pip_user_installed = False
    else:
        pip_user_installed = True
    if pip_user_installed:
        test_paths = (
            pip_user_path / "bin" / "pipx",
            Path(site.getusersitepackages()).resolve().parent / "Scripts" / "pipx.exe",
        )
        pipx_bin_path = None
        for test_path in test_paths:
            if test_path.exists():
                pipx_bin_path = test_path.parent
                break

    return pipx_bin_path


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
    pipx_user_bin_path = get_pipx_user_bin_path()
    if pipx_user_bin_path is not None:
        (path_added2, need_shell_restart2) = ensure_path(
            pipx_user_bin_path, force=force
        )
    else:
        (path_added2, need_shell_restart2) = (False, False)

    (path_added1, need_shell_restart1) = ensure_path(
        constants.LOCAL_BIN_DIR, force=force
    )

    if path_added1 or path_added2:
        print(
            "\nConsider adding shell completions for pipx.\n"
            "Run 'pipx completions' for instructions."
        )

    if need_shell_restart1 or need_shell_restart2:
        print(
            "\nYou likely need to open a new terminal or re-login for "
            "the PATH changes to take\neffect."
        )

    print(f"\nOtherwise pipx is ready to go! {stars}")
