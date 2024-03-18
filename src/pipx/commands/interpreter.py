from pathlib import Path
from typing import List

from pipx import constants, paths
from pipx.pipx_metadata_file import PipxMetadata
from pipx.util import is_paths_relative, rmdir
from pipx.venv import Venv, VenvContainer


def get_installed_standalone_interpreters() -> List[Path]:
    return [python_dir for python_dir in paths.ctx.standalone_python_cachedir.iterdir() if python_dir.is_dir()]


def get_venvs_using_standalone_interpreter(venv_container: VenvContainer) -> List[Venv]:
    venvs: list[Venv] = []
    for venv_dir in venv_container.iter_venv_dirs():
        venv = Venv(venv_dir)
        if venv.pipx_metadata.source_interpreter:
            venvs.append(venv)
    return venvs


def get_interpreter_users(interpreter: Path, venvs: List[Venv]) -> List[PipxMetadata]:
    return [
        venv.pipx_metadata
        for venv in venvs
        if venv.pipx_metadata.source_interpreter
        and is_paths_relative(venv.pipx_metadata.source_interpreter, interpreter)
    ]


def list_interpreters(
    venv_container: VenvContainer,
):
    interpreters = get_installed_standalone_interpreters()
    venvs = get_venvs_using_standalone_interpreter(venv_container)
    output: list[str] = []
    output.append(f"Standalone interpreters are in {paths.ctx.standalone_python_cachedir}")
    for interpreter in interpreters:
        output.append(f"Python {interpreter.name}")
        used_in = get_interpreter_users(interpreter, venvs)
        if used_in:
            output.append("    Used in:")
            for p in used_in:
                output.append(f"     - {p.main_package.package} {p.main_package.package_version}")
        else:
            output.append("    Unused")

    print("\n".join(output))
    return constants.EXIT_CODE_OK


def prune_interpreters(
    venv_container: VenvContainer,
):
    interpreters = get_installed_standalone_interpreters()
    venvs = get_venvs_using_standalone_interpreter(venv_container)
    removed = []
    for interpreter in interpreters:
        if get_interpreter_users(interpreter, venvs):
            continue
        rmdir(interpreter, safe_rm=True)
        removed.append(interpreter.name)
    if removed:
        print("Successfully removed:")
        for interpreter_name in removed:
            print(f" - Python {interpreter_name}")
    else:
        print("Nothing to remove")
    return constants.EXIT_CODE_OK
