import json
import sys
from pathlib import Path
from typing import Any, Collection, Dict, Tuple

from pipx import constants
from pipx.colors import bold
from pipx.commands.common import VenvProblems, get_venv_summary, venv_health_check
from pipx.constants import EXIT_CODE_LIST_PROBLEM, EXIT_CODE_OK, ExitCode
from pipx.emojis import sleep
from pipx.pipx_metadata_file import JsonEncoderHandlesPath, PipxMetadata
from pipx.venv import Venv, VenvContainer

PIPX_SPEC_VERSION = "0.1"


def get_venv_metadata_summary(venv_dir: Path) -> Tuple[PipxMetadata, VenvProblems, str]:
    venv = Venv(venv_dir)

    (venv_problems, warning_message) = venv_health_check(venv)
    if venv_problems.any_:
        return (PipxMetadata(venv_dir, read=False), venv_problems, warning_message)

    return (venv.pipx_metadata, venv_problems, "")


def list_text(
    venv_dirs: Collection[Path], include_injected: bool, venv_root_dir: str
) -> VenvProblems:
    print(f"venvs are in {bold(venv_root_dir)}")
    print(f"apps are exposed on your $PATH at {bold(str(constants.LOCAL_BIN_DIR))}")

    all_venv_problems = VenvProblems()
    for venv_dir in venv_dirs:
        package_summary, venv_problems = get_venv_summary(
            venv_dir, include_injected=include_injected
        )
        print(package_summary)
        all_venv_problems.or_(venv_problems)

    return all_venv_problems


def list_json(venv_dirs: Collection[Path]) -> VenvProblems:
    warning_messages = []
    spec_metadata: Dict[str, Any] = {
        "pipx_spec_version": PIPX_SPEC_VERSION,
        "venvs": {},
    }
    all_venv_problems = VenvProblems()
    for venv_dir in venv_dirs:
        (venv_metadata, venv_problems, warning_str) = get_venv_metadata_summary(
            venv_dir
        )
        all_venv_problems.or_(venv_problems)
        if venv_problems.any_:
            warning_messages.append(warning_str)
            continue

        spec_metadata["venvs"][venv_dir.name] = {}
        spec_metadata["venvs"][venv_dir.name]["metadata"] = venv_metadata.to_dict()

    print(
        json.dumps(spec_metadata, indent=4, sort_keys=True, cls=JsonEncoderHandlesPath)
    )
    for warning_message in warning_messages:
        print(warning_message, file=sys.stderr)

    return all_venv_problems


def list_packages(
    venv_container: VenvContainer, include_injected: bool, json_format: bool
) -> ExitCode:
    """Returns pipx exit code."""
    venv_dirs: Collection[Path] = sorted(venv_container.iter_venv_dirs())
    if not venv_dirs:
        print(f"nothing has been installed with pipx {sleep}")
        return EXIT_CODE_OK

    venv_container.verify_shared_libs()

    if json_format:
        all_venv_problems = list_json(venv_dirs)
    else:
        all_venv_problems = list_text(venv_dirs, include_injected, str(venv_container))

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

    if all_venv_problems.any_:
        print()
        return EXIT_CODE_LIST_PROBLEM

    return EXIT_CODE_OK
