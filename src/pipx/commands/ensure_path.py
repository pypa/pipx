import logging
import site
import sys
from pathlib import Path
from typing import Optional, Tuple

import userpath  # type: ignore[import-not-found]

from pipx import paths
from pipx.constants import EXIT_CODE_OK, ExitCode
from pipx.emojis import hazard, stars
from pipx.util import pipx_wrap

logger = logging.getLogger(__name__)


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


def ensure_path(location: Path, *, force: bool, prepend: bool = False) -> Tuple[bool, bool]:
    """Ensure location is in user's PATH or add it to PATH.
    If prepend is True, location will be prepended to PATH, else appended.
    Returns True if location was added to PATH
    """
    location_str = str(location)
    path_added = False
    need_shell_restart = userpath.need_shell_restart(location_str)
    in_current_path = userpath.in_current_path(location_str)

    if force or (not in_current_path and not need_shell_restart):
        if prepend:
            path_added = userpath.prepend(location_str, "pipx")
        else:
            path_added = userpath.append(location_str, "pipx")
        if not path_added:
            print(
                pipx_wrap(
                    f"{hazard}  {location_str} is not added to the PATH environment variable successfully. "
                    f"You may need to add it to PATH manually.",
                    subsequent_indent=" " * 4,
                )
            )
        else:
            print(
                pipx_wrap(
                    f"Success! Added {location_str} to the PATH environment variable.",
                    subsequent_indent=" " * 4,
                )
            )
        need_shell_restart = userpath.need_shell_restart(location_str)
    elif not in_current_path and need_shell_restart:
        print(
            pipx_wrap(
                f"""
                {location_str} has been been added to PATH, but you need to
                open a new terminal or re-login for this PATH change to take
                effect. Alternatively, you can source your shell's config file
                with e.g. 'source ~/.bashrc'.
                """,
                subsequent_indent=" " * 4,
            )
        )
    else:
        print(pipx_wrap(f"{location_str} is already in PATH.", subsequent_indent=" " * 4))

    return (path_added, need_shell_restart)


def ensure_pipx_paths(force: bool, prepend: bool = False) -> ExitCode:
    """Returns pipx exit code."""
    bin_paths = {paths.ctx.bin_dir}

    pipx_user_bin_path = get_pipx_user_bin_path()
    if pipx_user_bin_path is not None:
        bin_paths.add(pipx_user_bin_path)

    path_added = False
    need_shell_restart = False
    path_action_str = "prepended to" if prepend else "appended to"

    for bin_path in bin_paths:
        (path_added_current, need_shell_restart_current) = ensure_path(bin_path, prepend=prepend, force=force)
        path_added |= path_added_current
        need_shell_restart |= need_shell_restart_current

    print()

    if path_added:
        print(
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
        logger.warning(
            pipx_wrap(
                f"""
                {hazard}  All pipx binary directories have been {path_action_str} PATH. If you
                are sure you want to proceed, try again with the '--force'
                flag.
                """
            )
            + "\n"
        )

    if need_shell_restart:
        print(
            pipx_wrap(
                """
                You will need to open a new terminal or re-login for the PATH
                changes to take effect. Alternatively, you can source your shell's
                config file with e.g. 'source ~/.bashrc'.
                """
            )
            + "\n"
        )

    print(f"Otherwise pipx is ready to go! {stars}")

    return EXIT_CODE_OK
