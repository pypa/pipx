import json
import sys
from collections.abc import Iterator, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Final

from filelock import BaseFileLock
from packaging.utils import canonicalize_name

from pipx import commands, paths
from pipx.backends import PIP
from pipx.commands.common import (
    expose_package_resources,
    package_name_from_spec,
    run_post_install_actions,
    validate_expected_apps,
)
from pipx.commands.transaction import preserve_venv
from pipx.constants import (
    EXIT_CODE_INSTALL_VENV_EXISTS,
    EXIT_CODE_OK,
    ExitCode,
)
from pipx.emojis import sleep
from pipx.interpreter import get_default_python
from pipx.package_specifier import package_spec_satisfied
from pipx.pipx_metadata_file import PackageInfo, PipxMetadata, load_spec_file
from pipx.util import PipxError, pipx_wrap
from pipx.venv import Venv, VenvContainer


def install(
    venv_dir: Path | None,
    package_names: list[str] | None,
    package_specs: list[str],
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str | None,
    pip_args: list[str],
    venv_args: list[str],
    verbose: bool,
    *,
    force: bool,
    reinstall: bool,
    include_dependencies: bool,
    preinstall_packages: list[str] | None,
    expected_apps: Sequence[str] = (),
    suffix: str = "",
    python_flag_passed: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
    exposure_enabled: bool | None = None,
    upgrade: bool = False,
    upgrade_strategy: str | None = None,
    venv_lock: BaseFileLock | None = None,
) -> ExitCode:
    """Returns pipx exit code."""
    # package_spec is anything pip-installable, including package_name, vcs spec,
    #   zip file, or tar.gz file.

    _validate_install_options(package_specs, expected_apps, upgrade=upgrade, upgrade_strategy=upgrade_strategy)

    python = python or get_default_python()

    package_names = package_names or []
    if len(package_names) != len(package_specs):
        package_names = [
            package_name_from_spec(
                package_spec,
                python,
                pip_args=pip_args,
                verbose=verbose,
                backend=backend,
                env_backend=env_backend,
            )
            for package_spec in package_specs
        ]

    venv_container: Final[VenvContainer] = VenvContainer(venv_dir.parent if venv_dir is not None else paths.ctx.venvs)
    for package_name, package_spec in zip(package_names, package_specs, strict=False):
        if venv_dir is None:
            venv_dir = venv_container.get_venv_dir(f"{package_name}{suffix}")

        with venv_lock or venv_container.venv_lock(venv_dir):
            try:
                exists = venv_dir.exists() and bool(next(venv_dir.iterdir()))
            except StopIteration:
                exists = False

            # ``pipx install pip`` always uses pip (uv venvs ship no pip). Override
            # only the implicit env path; ``--backend uv`` still falls through to
            # ``assert_not_pip_under_uv`` so an explicit conflict fails loudly.
            install_backend, install_env_backend = backend, env_backend
            if canonicalize_name(package_name) == "pip":
                install_backend = backend or PIP
                install_env_backend = None

            venv = Venv(
                venv_dir,
                python=python,
                verbose=verbose,
                backend=install_backend,
                env_backend=install_env_backend,
            )
            required_apps = tuple(dict.fromkeys(expected_apps or venv.pipx_metadata.main_package.expected_apps))
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
                elif upgrade:
                    _upgrade_existing_venv(
                        venv,
                        package_name,
                        package_spec,
                        local_bin_dir,
                        local_man_dir,
                        pip_args,
                        verbose,
                        upgrade_strategy,
                        required_apps,
                    )
                    if len(package_specs) == 1:
                        return EXIT_CODE_OK
                    venv_dir = None
                    continue
                else:
                    installed_version = venv.pipx_metadata.main_package.package_version
                    version_info = f" ({installed_version})" if installed_version else ""
                    print(
                        pipx_wrap(
                            f"""
                            {venv.name!r}{version_info} already seems to be installed. Not
                            modifying existing installation in '{venv_dir}'.
                            Pass '--force' to force installation, or use
                            'pipx upgrade {venv.name}' to upgrade.
                            """
                        )
                    )
                    if len(package_specs) == 1:
                        return EXIT_CODE_INSTALL_VENV_EXISTS
                    venv_dir = None
                    continue

            with preserve_venv(venv_dir, enabled=exists and bool(required_apps)):
                venv.check_upgrade_shared_libs(pip_args=pip_args, verbose=verbose)
                try:
                    override_shared = canonicalize_name(package_name) == "pip"
                    venv.create_venv(venv_args, pip_args, override_shared)
                    venv.pipx_metadata.exposure_enabled = (
                        venv.pipx_metadata.exposure_enabled if exposure_enabled is None else exposure_enabled
                    )
                    for dependency in preinstall_packages or []:
                        venv.upgrade_package_no_metadata(dependency, [])
                    venv.install_package(
                        package_name=package_name,
                        package_or_url=package_spec,
                        pip_args=pip_args,
                        install_only_pip_args=["--force-reinstall"] if force and exists else None,
                        include_dependencies=include_dependencies,
                        include_apps=True,
                        is_main_package=True,
                        suffix=suffix,
                        expected_apps=required_apps,
                    )
                    validate_expected_apps(venv, package_name, required_apps)
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
        venv_dir = None

    return EXIT_CODE_OK


def _validate_install_options(
    package_specs: Sequence[str],
    expected_apps: Sequence[str],
    *,
    upgrade: bool,
    upgrade_strategy: str | None,
) -> None:
    if upgrade_strategy is not None and not upgrade:
        raise PipxError("--upgrade-strategy requires --upgrade")
    if expected_apps and len(package_specs) != 1:
        raise PipxError("--app accepts one package spec")


def _upgrade_existing_venv(
    venv: Venv,
    package_name: str,
    package_spec: str,
    local_bin_dir: Path,
    local_man_dir: Path,
    pip_args: list[str],
    verbose: bool,
    upgrade_strategy: str | None,
    expected_apps: Sequence[str],
) -> None:
    package_metadata = venv.pipx_metadata.main_package
    installed_version: Final[str] = package_metadata.package_version
    if package_spec_satisfied(
        package_spec,
        package_name,
        installed_version,
        package_metadata.package_or_url or package_name,
    ):
        validate_expected_apps(venv, package_name, expected_apps)
        _record_expected_apps(venv, expected_apps)
        print(f"{package_name} {installed_version} already satisfies {package_spec}")
        return
    if package_metadata.pinned:
        validate_expected_apps(venv, package_name, expected_apps)
        _record_expected_apps(venv, expected_apps)
        print(f"Not upgrading pinned package {venv.name}. Run `pipx unpin {venv.name}` to unpin it.")
        return

    with preserve_venv(venv.root, enabled=bool(expected_apps)):
        main_pip_args: Final[list[str]] = pip_args or package_metadata.pip_args
        venv.check_upgrade_shared_libs(pip_args=main_pip_args, verbose=verbose)
        venv.upgrade_packaging_libraries(main_pip_args)
        venv.upgrade_package(
            package_name,
            package_spec,
            main_pip_args,
            include_dependencies=package_metadata.include_dependencies,
            include_apps=package_metadata.include_apps,
            is_main_package=True,
            suffix=package_metadata.suffix,
            upgrade_only_pip_args=([f"--upgrade-strategy={upgrade_strategy}"] if upgrade_strategy is not None else None),
            expected_apps=expected_apps,
        )
        validate_expected_apps(venv, package_name, expected_apps)
        package_metadata = venv.pipx_metadata.main_package
        if venv.pipx_metadata.exposure_enabled:
            expose_package_resources(package_metadata, local_bin_dir, local_man_dir, force=False)
    print(
        pipx_wrap(
            f"""
            upgraded package {venv.name} from {installed_version} to
            {package_metadata.package_version} (location: {venv.root!s})
            """
        )
    )


def _record_expected_apps(venv: Venv, expected_apps: Sequence[str]) -> None:
    expected: Final[list[str]] = list(dict.fromkeys(expected_apps))
    if venv.pipx_metadata.main_package.expected_apps == expected:
        return
    venv.pipx_metadata.main_package = replace(venv.pipx_metadata.main_package, expected_apps=expected)
    venv.pipx_metadata.write()


def install_all(
    spec_metadata_file: Path,
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str | None,
    pip_args: list[str],
    venv_args: list[str],
    verbose: bool,
    *,
    force: bool,
    backend: str | None = None,
    env_backend: str | None = None,
) -> ExitCode:
    venv_container: Final[VenvContainer] = VenvContainer(paths.ctx.venvs)
    failed: Final[list[str]] = []
    installed: Final[list[str]] = []

    for venv_metadata in extract_venv_metadata(spec_metadata_file):
        main_package = venv_metadata.main_package
        venv_dir = venv_container.get_venv_dir(f"{main_package.package}{main_package.suffix}")
        try:
            with venv_container.venv_lock(venv_dir) as venv_lock:
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
                    expected_apps=main_package.expected_apps,
                    suffix=main_package.suffix,
                    backend=backend or venv_metadata.backend,
                    env_backend=env_backend,
                    exposure_enabled=venv_metadata.exposure_enabled,
                    venv_lock=venv_lock,
                )
                for inject_package in venv_metadata.injected_packages.values():
                    commands.inject(
                        venv_dir=venv_dir,
                        package_specs=[generate_package_spec(inject_package)],
                        requirement_files=[],
                        pip_args=pip_args,
                        verbose=verbose,
                        include_apps=inject_package.include_apps,
                        include_dependencies=inject_package.include_dependencies,
                        force=force,
                        suffix=inject_package.suffix == main_package.suffix,
                    )
        except PipxError as error:
            print(error, file=sys.stderr)
            failed.append(venv_dir.name)
        else:
            installed.append(venv_dir.name)
    if not installed:
        print(f"No packages installed after running 'pipx install-all {spec_metadata_file}' {sleep}")
    if failed:
        raise PipxError(f"The following package(s) failed to install: {', '.join(failed)}")
    return EXIT_CODE_OK


def extract_venv_metadata(spec_metadata_file: Path) -> Iterator[PipxMetadata]:
    try:
        spec: Final = load_spec_file(spec_metadata_file)
    except json.decoder.JSONDecodeError as exc:
        raise PipxError("The spec metadata file is an invalid JSON file.") from exc

    venvs_metadata_dict: Final = spec.get("venvs")
    if not venvs_metadata_dict:
        raise PipxError("No packages found in the spec metadata file.")
    if not isinstance(venvs_metadata_dict, dict):
        raise PipxError("The spec metadata file is invalid.")

    for package_path_name, entry in venvs_metadata_dict.items():
        venv_dir = paths.ctx.venvs.joinpath(package_path_name)
        venv_metadata = PipxMetadata(venv_dir, read=False)
        venv_metadata.from_dict(entry["metadata"])
        yield venv_metadata


def generate_package_spec(package_info: PackageInfo) -> str:
    """Generate more precise package spec from package info."""
    if not package_info.package_or_url:
        raise PipxError(f"A package spec is not available for {package_info.package}")

    if package_info.package == package_info.package_or_url:
        return f"{package_info.package}=={package_info.package_version}"
    return package_info.package_or_url


def get_python_interpreter(
    source_interpreter: Path | None,
) -> str | None:
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


__all__ = [
    "extract_venv_metadata",
    "generate_package_spec",
    "get_python_interpreter",
    "install",
    "install_all",
]
