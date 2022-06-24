import json
import re
from pathlib import Path
from typing import List, Optional

from pipx import constants
from pipx.commands.common import package_name_from_spec, run_post_install_actions
from pipx.constants import EXIT_CODE_INSTALL_VENV_EXISTS, EXIT_CODE_OK, ExitCode
from pipx.interpreter import _get_absolute_python_interpreter
from pipx.util import PipxError, pipx_wrap
from pipx.venv import Venv, VenvContainer


def install(
    venv_dir: Optional[Path],
    package_name: Optional[str],
    package_spec: str,
    local_bin_dir: Path,
    python: str,
    pip_args: List[str],
    venv_args: List[str],
    verbose: bool,
    *,
    force: bool,
    include_dependencies: bool,
    suffix: str = "",
) -> ExitCode:
    """Returns pipx exit code."""
    # package_spec is anything pip-installable, including package_name, vcs spec,
    #   zip file, or tar.gz file.

    if package_name is None:
        package_name = package_name_from_spec(
            package_spec, python, pip_args=pip_args, verbose=verbose
        )
    if venv_dir is None:
        venv_container = VenvContainer(constants.PIPX_LOCAL_VENVS)
        venv_dir = venv_container.get_venv_dir(f"{package_name}{suffix}")

    try:
        exists = venv_dir.exists() and bool(next(venv_dir.iterdir()))
    except StopIteration:
        exists = False

    venv = Venv(venv_dir, python=python, verbose=verbose)
    if exists:
        if force:
            print(f"Installing to existing venv {venv.name!r}")
        else:
            print(
                pipx_wrap(
                    f"""
                    {venv.name!r} already seems to be installed. Not modifying
                    existing installation in {str(venv_dir)!r}. Pass '--force'
                    to force installation.
                    """
                )
            )
            return EXIT_CODE_INSTALL_VENV_EXISTS

    try:
        venv.create_venv(venv_args, pip_args)
        venv.install_package(
            package_name=package_name,
            package_or_url=package_spec,
            pip_args=pip_args,
            include_dependencies=include_dependencies,
            include_apps=True,
            is_main_package=True,
            suffix=suffix,
        )
        run_post_install_actions(
            venv,
            package_name,
            local_bin_dir,
            venv_dir,
            include_dependencies,
            force=force,
        )
    except (Exception, KeyboardInterrupt):
        print()
        venv.remove_venv()
        raise

    # Any failure to install will raise PipxError, otherwise success
    return EXIT_CODE_OK


def install_all(
    json_file: Path,
    venv_dir: Optional[Path],
    local_bin_dir: Path,
    verbose: bool,
    *,
    force: bool,
) -> ExitCode:

    install_success_count = 0
    total_package_count = 0

    with open(json_file, "r") as f:
        try:
            data = json.load(f)

            venvs = data["venvs"]

            for package in venvs:
                package_name = venvs[package]["metadata"]["main_package"]["package"]
                package_or_url = venvs[package]["metadata"]["main_package"][
                    "package_or_url"
                ]
                python_version = (
                    "python"
                    + re.findall(
                        r"\d.\d+", venvs[package]["metadata"]["python_version"]
                    )[0]
                )
                venv_args = venvs[package]["metadata"]["venv_args"]
                pip_args = venvs[package]["metadata"]["main_package"]["pip_args"]
                include_dependencies = venvs[package]["metadata"]["main_package"][
                    "include_dependencies"
                ]
                suffix = venvs[package]["metadata"]["main_package"]["suffix"]

                total_package_count += 1

                try:
                    install(
                        venv_dir=venv_dir,
                        package_name=package_name,
                        package_spec=package_or_url,
                        local_bin_dir=local_bin_dir,
                        python=_get_absolute_python_interpreter(python_version),
                        pip_args=pip_args,
                        venv_args=venv_args,
                        verbose=verbose,
                        force=force,
                        include_dependencies=include_dependencies,
                        suffix=suffix,
                    )

                    install_success_count += 1

                except Exception as e:
                    print(str(e))
                    print(f"Having errors when installing {package_name}. Skipping...")
                    print()
                    pass

        except json.decoder.JSONDecodeError:
            raise PipxError("Invalid JSON file.")

    print(f"Found {total_package_count} packages from {json_file}")
    print(f"Successfully installed {install_success_count} packages.")

    return EXIT_CODE_OK
