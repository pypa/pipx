from pathlib import Path
from typing import Collection

from pipx import constants
from pipx.colors import bold
from pipx.commands.common import VenvProblems, get_package_summary
from pipx.constants import EXIT_CODE_LIST_PROBLEM, EXIT_CODE_OK, ExitCode
from pipx.emojis import sleep
from pipx.venv import VenvContainer


def list_packages(venv_container: VenvContainer, include_injected: bool) -> ExitCode:
    """Returns pipx exit code."""
    venv_dirs: Collection[Path] = sorted(venv_container.iter_venv_dirs())
    if not venv_dirs:
        print(f"nothing has been installed with pipx {sleep}")
        return EXIT_CODE_OK

    print(f"venvs are in {bold(str(venv_container))}")
    print(f"apps are exposed on your $PATH at {bold(str(constants.LOCAL_BIN_DIR))}")

    venv_container.verify_shared_libs()

    all_venv_problems = VenvProblems()
    for venv_dir in venv_dirs:
        package_summary, venv_problems = get_package_summary(
            venv_dir, include_injected=include_injected
        )
        print(package_summary)
        all_venv_problems.or_(venv_problems)

    if all_venv_problems.bad_venv_name:
        print(
            "\nOne or more packages contain out-of-date internal data installed from a\n"
            "previous pipx version and need to be updated.\n"
            "    To fix, execute: pipx reinstall-all"
        )
    if all_venv_problems.invalid_interpreter:
        print(
            "\nOne or more packages have a missing python interpreter.\n"
            "    To fix, execute: pipx reinstall-all"
        )
    if all_venv_problems.missing_metadata:
        print(
            "\nOne or more packages have a missing internal pipx metadata.\n"
            "   They were likely installed using a pipx version before 0.15.0.0.\n"
            "   Please uninstall and install these package(s) to fix."
        )
    if all_venv_problems.not_installed:
        print(
            "\nOne or more packages are not installed properly.\n"
            "   Please uninstall and install these package(s) to fix."
        )

    if all_venv_problems.any_():
        print()
        return EXIT_CODE_LIST_PROBLEM

    return EXIT_CODE_OK
