import logging
import subprocess
from pathlib import Path
from typing import List

from packaging import version

from pipx import commands, constants, paths, standalone_python
from pipx.animate import animate
from pipx.pipx_metadata_file import PipxMetadata
from pipx.util import is_paths_relative, rmdir
from pipx.venv import Venv, VenvContainer

logger = logging.getLogger(__name__)


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
            output.extend(f"     - {p.main_package.package} {p.main_package.package_version}" for p in used_in)
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


def get_latest_micro_version(
    current_version: version.Version, latest_python_versions: List[version.Version]
) -> version.Version:
    for latest_python_version in latest_python_versions:
        if current_version.major == latest_python_version.major and current_version.minor == latest_python_version.minor:
            return latest_python_version
    return current_version


def upgrade_interpreters(venv_container: VenvContainer, verbose: bool):
    with animate("Getting the index of the latest standalone python builds", not verbose):
        latest_pythons = standalone_python.list_pythons(use_cache=False)

    parsed_latest_python_versions = []
    for latest_python_version in latest_pythons:
        try:
            parsed_latest_python_versions.append(version.parse(latest_python_version))
        except version.InvalidVersion:
            logger.info(f"Invalid version found in latest pythons: {latest_python_version}. Skipping.")

    upgraded = []

    for interpreter_dir in paths.ctx.standalone_python_cachedir.iterdir():
        if not interpreter_dir.is_dir():
            continue

        interpreter_python = interpreter_dir / "python.exe" if constants.WINDOWS else interpreter_dir / "bin" / "python3"
        interpreter_full_version = (
            subprocess.run([str(interpreter_python), "--version"], stdout=subprocess.PIPE, check=True, text=True)
            .stdout.strip()
            .split()[1]
        )
        try:
            parsed_interpreter_full_version = version.parse(interpreter_full_version)
        except version.InvalidVersion:
            logger.info(f"Invalid version found in interpreter at {interpreter_dir}. Skipping.")
            continue
        latest_micro_version = get_latest_micro_version(parsed_interpreter_full_version, parsed_latest_python_versions)
        if latest_micro_version > parsed_interpreter_full_version:
            standalone_python.download_python_build_standalone(
                f"{latest_micro_version.major}.{latest_micro_version.minor}",
                override=True,
            )

            for venv_dir in venv_container.iter_venv_dirs():
                venv = Venv(venv_dir)
                if venv.pipx_metadata.source_interpreter is not None and is_paths_relative(
                    venv.pipx_metadata.source_interpreter, interpreter_dir
                ):
                    print(
                        f"Upgrade the interpreter of {venv.name} from {interpreter_full_version} to {latest_micro_version}"
                    )
                    commands.reinstall(
                        venv_dir=venv_dir,
                        local_bin_dir=paths.ctx.bin_dir,
                        local_man_dir=paths.ctx.man_dir,
                        python=str(interpreter_python),
                        verbose=verbose,
                    )
                    upgraded.append((venv.name, interpreter_full_version, latest_micro_version))

    if upgraded:
        print("Successfully upgraded the interpreter(s):")
        for venv_name, old_version, new_version in upgraded:
            print(f" - {venv_name}: {old_version} -> {new_version}")
    else:
        print("Nothing to upgrade")

    # Any failure to upgrade will raise PipxError, otherwise success
    return constants.EXIT_CODE_OK
