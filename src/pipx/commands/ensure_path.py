import logging
from pathlib import Path

import userpath  # type: ignore
from pipx.emojies import stars


def ensure_path(location: Path, *, force: bool):
    location_str = str(location)

    post_install_message = (
        "You likely need to open a new terminal or re-login for "
        "the changes to take effect."
    )
    if userpath.in_current_path(location_str) or userpath.need_shell_restart(
        location_str
    ):
        if not force:
            if userpath.need_shell_restart(location_str):
                print(
                    f"{location_str} has been already been added to PATH. "
                    f"{post_install_message}"
                )
            else:
                logging.warning(
                    (
                        f"The directory `{location_str}` is already in PATH. If you "
                        "are sure you want to proceed, try again with "
                        "the '--force' flag.\n\n"
                        f"Otherwise pipx is ready to go! {stars}"
                    )
                )
            return

    userpath.append(location_str)
    print(f"Success! Added {location_str} to the PATH environment variable.")
    print(
        "Consider adding shell completions for pipx. "
        "Run 'pipx completions' for instructions."
    )
    print()
    print(f"{post_install_message} {stars}")
