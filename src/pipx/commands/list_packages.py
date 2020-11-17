from functools import partial
from pathlib import Path
from typing import Callable, Collection, Optional

from pipx import constants
from pipx.colors import bold
from pipx.commands.common import get_package_summary
from pipx.constants import EXIT_CODE_LIST_PROBLEM, EXIT_CODE_OK
from pipx.emojies import sleep
from pipx.venv import VenvContainer

Pool: Optional[Callable]
try:
    import multiprocessing.synchronize  # noqa: F401
    from multiprocessing import Pool
except ImportError:
    Pool = None


def list_packages(venv_container: VenvContainer, include_injected: bool) -> int:
    """Returns pipx exit code."""
    dirs: Collection[Path] = sorted(venv_container.iter_venv_dirs())
    if not dirs:
        print(f"nothing has been installed with pipx {sleep}")
        return EXIT_CODE_OK

    print(f"venvs are in {bold(str(venv_container))}")
    print(f"apps are exposed on your $PATH at {bold(str(constants.LOCAL_BIN_DIR))}")

    venv_container.verify_shared_libs()

    all_venv_errors = {
        "invalid_interpreter": False,
        "missing_metadata": False,
        "not_installed": False,
    }
    if Pool:
        p = Pool()
        try:
            for package_summary, venv_errors in p.map(
                partial(get_package_summary, include_injected=include_injected), dirs
            ):
                print(package_summary)
                all_venv_errors["invalid_interpreter"] |= venv_errors.get(
                    "invalid_interpreter", False
                )
                all_venv_errors["missing_metadata"] |= venv_errors.get(
                    "missing_metadata", False
                )
                all_venv_errors["not_installed"] |= venv_errors.get(
                    "not_installed", False
                )

        finally:
            p.close()
            p.join()
    else:
        for package_summary, venv_errors in map(
            partial(get_package_summary, include_injected=include_injected), dirs
        ):
            print(package_summary)
            all_venv_errors["invalid_interpreter"] |= venv_errors.get(
                "invalid_interpreter", False
            )
            all_venv_errors["missing_metadata"] |= venv_errors.get(
                "missing_metadata", False
            )
            all_venv_errors["not_installed"] |= venv_errors.get("not_installed", False)

    if all_venv_errors["invalid_interpreter"]:
        print(
            "\nOne or more packages have a missing python interpreter.\n"
            "    To fix, execute: pipx reinstall-all"
        )
    if all_venv_errors["missing_metadata"]:
        print(
            "\nOne or more packages have a missing internal pipx metadata.\n"
            "   They were likely installed using a pipx version before 0.15.0.0.\n"
            "   Please uninstall and install these package(s) to fix."
        )
    if all_venv_errors["not_installed"]:
        print(
            "\nOne or more packages are not installed properly.\n"
            "   Please uninstall and install these package(s) to fix."
        )

    if (
        all_venv_errors["invalid_interpreter"]
        or all_venv_errors["missing_metadata"]
        or all_venv_errors["not_installed"]
    ):
        print()
        return EXIT_CODE_LIST_PROBLEM

    return EXIT_CODE_OK
