import json
from functools import partial
from pathlib import Path
from typing import Callable, Collection, List, Optional

from pipx import constants
from pipx.colors import bold
from pipx.commands.common import VenvProblems, get_package_summary
from pipx.constants import EXIT_CODE_LIST_PROBLEM, EXIT_CODE_OK, ExitCode
from pipx.emojies import sleep
from pipx.util import PipxError
from pipx.venv import Venv, VenvContainer

Pool: Optional[Callable]
try:
    import multiprocessing.synchronize  # noqa: F401
    from multiprocessing import Pool
except ImportError:
    Pool = None


def list_packages(
    venv_container: VenvContainer, include_injected: bool, format: str
) -> ExitCode:
    """Returns pipx exit code."""
    dirs: Collection[Path] = sorted(venv_container.iter_venv_dirs())
    if not dirs:
        print(f"nothing has been installed with pipx {sleep}")
        return EXIT_CODE_OK

    venv_container.verify_shared_libs()

    if format == "human":
        print(f"venvs are in {bold(str(venv_container))}")
        print(f"apps are exposed on your $PATH at {bold(str(constants.LOCAL_BIN_DIR))}")

        return _print_packages_and_check_venv_problems(dirs, include_injected)

    elif format == "freeze":
        return _print_packages_as_pip_freeze(dirs)

    elif format == "json":
        return _print_packages_as_json(dirs, include_injected)

    else:
        raise PipxError(f"Unsupported format for list: '{format}'")

    return EXIT_CODE_OK


def _print_packages_and_check_venv_problems(
    dirs: Collection[Path], include_injected: bool
) -> ExitCode:
    all_venv_problems = VenvProblems()
    if Pool:
        p = Pool()
        try:
            for package_summary, venv_problems in p.map(
                partial(get_package_summary, include_injected=include_injected), dirs
            ):
                print(package_summary)
                all_venv_problems.or_(venv_problems)
        finally:
            p.close()
            p.join()
    else:
        for package_summary, venv_problems in map(
            partial(get_package_summary, include_injected=include_injected), dirs
        ):
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


def _print_packages_as_pip_freeze(dirs: Collection[Path]) -> ExitCode:
    packages = ""
    for venv_dir in dirs:
        venv = Venv(venv_dir)
        main_pkg = venv.pipx_metadata.main_package
        packages += f"{main_pkg.package_or_url}=={main_pkg.package_version}\n"
    print(packages)

    return EXIT_CODE_OK


def _print_packages_as_json(dirs: Collection[Path], include_injected: bool) -> ExitCode:
    class JSONEncoder(json.JSONEncoder):
        """OVerloaded JSON Encoder to properly handle Path objects."""

        def default(self, obj):
            if isinstance(obj, Path):
                return str(obj)

            return json.JSONEncoder.default(self, obj)

    packages: List[dict] = []
    for venv_dir in dirs:
        venv = Venv(venv_dir)
        package_metadata = venv.pipx_metadata.to_dict()
        if not include_injected:
            del package_metadata["injected_packages"]

        packages.append(package_metadata)
    print(json.dumps(packages, cls=JSONEncoder))

    return EXIT_CODE_OK
