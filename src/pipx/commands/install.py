import json
import sys
from pathlib import Path
from typing import Iterator, List, Optional

from pipx import commands, paths
from pipx.commands.common import package_name_from_spec, run_post_install_actions
from pipx.constants import (
    EXIT_CODE_INSTALL_VENV_EXISTS,
    EXIT_CODE_OK,
    ExitCode,
)
from pipx.emojis import sleep
from pipx.interpreter import DEFAULT_PYTHON
from pipx.pipx_metadata_file import PackageInfo, PipxMetadata, _json_decoder_object_hook
from pipx.util import PipxError, pipx_wrap
from pipx.venv import Venv, VenvContainer


def install(
    venv_dir: Optional[Path],
    package_names: Optional[List[str]],
    package_specs: List[str],
    local_bin_dir: Path,
    local_man_dir: Path,
    python: Optional[str],
    pip_args: List[str],
    venv_args: List[str],
    verbose: bool,
    *,
    force: bool,
    reinstall: bool,
    include_dependencies: bool,
    preinstall_packages: Optional[List[str]],
    suffix: str = "",
    python_flag_passed=False,
) -> ExitCode:
    """Returns pipx exit code."""
    # package_spec is anything pip-installable, including package_name, vcs spec,
    #   zip file, or tar.gz file.

    python = python or DEFAULT_PYTHON

    package_names = package_names or []
    if len(package_names) != len(package_specs):
        package_names = [
            package_name_from_spec(package_spec, python, pip_args=pip_args, verbose=verbose)
            for package_spec in package_specs
        ]

    for package_name, package_spec in zip(package_names, package_specs):
        if venv_dir is None:
            venv_container = VenvContainer(paths.ctx.venvs)
            venv_dir = venv_container.get_venv_dir(f"{package_name}{suffix}")

        try:
            exists = venv_dir.exists() and bool(next(venv_dir.iterdir()))
        except StopIteration:
            exists = False

        venv = Venv(venv_dir, python=python, verbose=verbose)
        venv.check_upgrade_shared_libs(pip_args=pip_args, verbose=verbose)
        if exists:
            if not reinstall and force and python_flag_passed:
                print(
                    pipx_wrap(
                        f"""
                        --python is ignored when --force is passed.
                        If you want to reinstall {package_name} with {python},
                        run `pipx reinstall {package_spec} --python {python}` instead.
                        """
                    )
                )
            if force:
                print(f"Installing to existing venv {venv.name!r}")
                pip_args = ["--force-reinstall"] + pip_args
            else:
                print(
                    pipx_wrap(
                        f"""
                        {venv.name!r} already seems to be installed. Not modifying
                        existing installation in '{venv_dir}'. Pass '--force'
                        to force installation.
                        """
                    )
                )
                if len(package_specs) == 1:
                    return EXIT_CODE_INSTALL_VENV_EXISTS
                # Reset venv_dir to None ready to install the next package in the list
                venv_dir = None
                continue

        try:
            # Enable installing shared library `pip` with `pipx`
            override_shared = package_name == "pip"
            venv.create_venv(venv_args, pip_args, override_shared)
            for dep in preinstall_packages or []:
                venv.upgrade_package_no_metadata(dep, [])
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
                local_man_dir,
                venv_dir,
                include_dependencies,
                force=force,
            )
        except (Exception, KeyboardInterrupt):
            print()
            venv.remove_venv()
            raise

        # Reset venv_dir to None ready to install the next package in the list
        venv_dir = None

    # Any failure to install will raise PipxError, otherwise success
    return EXIT_CODE_OK


def extract_venv_metadata(spec_metadata_file: Path) -> Iterator[PipxMetadata]:
    """Extract venv metadata from spec metadata file."""
    with open(spec_metadata_file) as spec_metadata_fh:
        try:
            spec_metadata_dict = json.load(spec_metadata_fh, object_hook=_json_decoder_object_hook)
        except json.decoder.JSONDecodeError as exc:
            raise PipxError("The spec metadata file is an invalid JSON file.") from exc

        if not ("venvs" in spec_metadata_dict and len(spec_metadata_dict["venvs"])):
            raise PipxError("No packages found in the spec metadata file.")

        venvs_metadata_dict = spec_metadata_dict["venvs"]

        if not isinstance(venvs_metadata_dict, dict):
            raise PipxError("The spec metadata file is invalid.")

        for package_path_name in venvs_metadata_dict:
            venv_dir = paths.ctx.venvs.joinpath(package_path_name)
            venv_metadata = PipxMetadata(venv_dir, read=False)
            venv_metadata.from_dict(venvs_metadata_dict[package_path_name]["metadata"])
            yield venv_metadata


def generate_package_spec(package_info: PackageInfo) -> str:
    """Generate more precise package spec from package info."""
    if not package_info.package_or_url:
        raise PipxError(f"A package spec is not available for {package_info.package}")

    if package_info.package == package_info.package_or_url:
        return f"{package_info.package}=={package_info.package_version}"
    return package_info.package_or_url


def get_python_interpreter(
    source_interpreter: Optional[Path],
) -> Optional[str]:
    """Get appropriate python interpreter."""
    if source_interpreter is not None and source_interpreter.is_file():
        return str(source_interpreter)

    print(
        pipx_wrap(
            f"""
            The exported python interpreter '{source_interpreter}' is ignored
            as not found.
            """
        )
    )

    return None


def install_all(
    spec_metadata_file: Path,
    local_bin_dir: Path,
    local_man_dir: Path,
    python: Optional[str],
    pip_args: List[str],
    venv_args: List[str],
    verbose: bool,
    *,
    force: bool,
) -> ExitCode:
    """Return pipx exit code."""
    venv_container = VenvContainer(paths.ctx.venvs)
    failed: List[str] = []
    installed: List[str] = []

    for venv_metadata in extract_venv_metadata(spec_metadata_file):
        # Install the main package
        main_package = venv_metadata.main_package
        venv_dir = venv_container.get_venv_dir(f"{main_package.package}{main_package.suffix}")
        try:
            install(
                venv_dir,
                None,
                [generate_package_spec(main_package)],
                local_bin_dir,
                local_man_dir,
                python or get_python_interpreter(venv_metadata.source_interpreter),
                pip_args,
                venv_args,
                verbose,
                force=force,
                reinstall=False,
                include_dependencies=main_package.include_dependencies,
                preinstall_packages=[],
                suffix=main_package.suffix,
            )

            # Install the injected packages
            for inject_package in venv_metadata.injected_packages.values():
                commands.inject(
                    venv_dir=venv_dir,
                    package_name=None,
                    package_specs=[generate_package_spec(inject_package)],
                    requirement_files=[],
                    pip_args=pip_args,
                    verbose=verbose,
                    include_apps=inject_package.include_apps,
                    include_dependencies=inject_package.include_dependencies,
                    force=force,
                    suffix=inject_package.suffix == main_package.suffix,
                )
        except PipxError as e:
            print(e, file=sys.stderr)
            failed.append(venv_dir.name)
        else:
            installed.append(venv_dir.name)
    if len(installed) == 0:
        print(f"No packages installed after running 'pipx install-all {spec_metadata_file}' {sleep}")
    if len(failed) > 0:
        raise PipxError(f"The following package(s) failed to install: {', '.join(failed)}")
    # Any failure to install will raise PipxError, otherwise success
    return EXIT_CODE_OK
