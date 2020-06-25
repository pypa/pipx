import logging
from pathlib import Path
import site
import textwrap
from typing import Tuple, Optional

import userpath  # type: ignore
from pipx.emojies import stars
from pipx import constants


def wrap_indent(text: str) -> str:
    text_wrapped = textwrap.wrap(text)
    if len(text_wrapped) > 1:
        return (
            text_wrapped[0]
            + "\n"
            + textwrap.indent("\n".join(text_wrapped[1:]), "    ")
        )
    else:
        return text_wrapped[0]


def get_pipx_user_bin_path() -> Optional[Path]:
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
    path_added = False
    need_shell_restart = userpath.need_shell_restart(location_str)
    in_current_path = userpath.in_current_path(location_str)

    if force or (not in_current_path and not need_shell_restart):
        userpath.append(location_str)
        print(
            wrap_indent(
                f"Success! Added {location_str} to the PATH environment variable."
            )
        )
        path_added = True
        need_shell_restart = userpath.need_shell_restart(location_str)
    elif not in_current_path and need_shell_restart:
        print(
            wrap_indent(
                f"{location_str} has been been added to PATH, but you "
                "need to open a new terminal or re-login for the PATH "
                "changes to take effect."
            )
        )
    else:
        print(wrap_indent(f"{location_str} is already in PATH."))

    return (path_added, need_shell_restart)


def ensure_pipx_paths(force: bool):
    pipx_user_bin_path = get_pipx_user_bin_path()
    if pipx_user_bin_path is not None:
        (path_added_pipx, need_shell_restart_pipx) = ensure_path(
            pipx_user_bin_path, force=force
        )
    else:
        (path_added_pipx, need_shell_restart_pipx) = (False, False)

    (path_added_bindir, need_shell_restart_bindir) = ensure_path(
        constants.LOCAL_BIN_DIR, force=force
    )
    print()

    if path_added_pipx or path_added_bindir:
        print(
            textwrap.fill(
                "Consider adding shell completions for pipx. "
                "Run 'pipx completions' for instructions."
            )
            + "\n"
        )
    else:
        logging.warning(
            textwrap.fill(
                "All pipx binary directories have been added to PATH. "
                "If you are sure you want add them again, try again with "
                "the '--force' flag."
            )
            + "\n"
        )

    if need_shell_restart_pipx or need_shell_restart_bindir:
        print(
            textwrap.fill(
                "You likely need to open a new terminal or re-login for "
                "the PATH changes to take effect."
            )
            + "\n"
        )

    print(f"Otherwise pipx is ready to go! {stars}")
