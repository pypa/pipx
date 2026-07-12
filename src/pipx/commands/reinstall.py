import sys
from collections.abc import Sequence
from pathlib import Path
from tempfile import mkdtemp

from packaging.utils import canonicalize_name

from pipx.commands.common import add_suffix
from pipx.commands.inject import inject_dep
from pipx.commands.install import install
from pipx.commands.uninstall import _get_venv_package_infos, _get_venv_resource_paths
from pipx.constants import (
    EXIT_CODE_OK,
    EXIT_CODE_REINSTALL_INVALID_PYTHON,
    EXIT_CODE_REINSTALL_VENV_NONEXISTENT,
    MAN_SECTIONS,
    ExitCode,
)
from pipx.emojis import error, sleep, stars
from pipx.util import PipxError, rmdir, safe_unlink
from pipx.venv import Venv, VenvContainer


def _create_reinstall_backup(venv_dir: Path) -> Path:
    backup_dir = Path(mkdtemp(prefix=f".{venv_dir.name}-", suffix="-pipx-reinstall", dir=venv_dir.parent))
    backup_dir.rmdir()
    venv_dir.rename(backup_dir)
    return backup_dir


def _restore_reinstall_backup(venv_dir: Path, restore_venv_dir: Path, backup_dir: Path) -> None:
    rmdir(venv_dir)
    backup_dir.rename(restore_venv_dir)


def _get_reinstall_resource_paths(venv: Venv, local_bin_dir: Path, local_man_dir: Path) -> set[Path]:
    package_infos = _get_venv_package_infos(venv)
    resource_paths = _get_venv_resource_paths("app", venv.bin_path, local_bin_dir, package_infos)
    for man_section in MAN_SECTIONS:
        resource_paths |= _get_venv_resource_paths(
            "man", venv.man_path / man_section, local_man_dir / man_section, package_infos
        )
    return resource_paths


def _get_expected_reinstall_resource_paths(venv: Venv, local_bin_dir: Path, local_man_dir: Path) -> set[Path]:
    resource_paths: set[Path] = set()
    for package_info in venv.package_metadata.values():
        if package_info.include_apps:
            for app_path in package_info.app_paths:
                resource_paths.add(local_bin_dir / add_suffix(app_path.name, package_info.suffix))
            for man_path in package_info.man_paths:
                resource_paths.add(local_man_dir / man_path.parent.name / man_path.name)
        if package_info.include_dependencies:
            for app_paths in package_info.app_paths_of_dependencies.values():
                for app_path in app_paths:
                    resource_paths.add(local_bin_dir / add_suffix(app_path.name, package_info.suffix))
            for man_paths in package_info.man_paths_of_dependencies.values():
                for man_path in man_paths:
                    resource_paths.add(local_man_dir / man_path.parent.name / man_path.name)
    return resource_paths


def _remove_stale_reinstall_resources(resource_paths: set[Path]) -> None:
    for path in sorted(resource_paths):
        try:
            safe_unlink(path)
            if path.is_symlink():
                path.unlink()
        except FileNotFoundError:
            pass


def reinstall(
    *,
    venv_dir: Path,
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str,
    verbose: bool,
    force_reinstall_shared_libs: bool = False,
    python_flag_passed: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
) -> ExitCode:
    """Returns pipx exit code."""
    if not venv_dir.exists():
        print(f"Nothing to reinstall for {venv_dir.name} {sleep}")
        return EXIT_CODE_REINSTALL_VENV_NONEXISTENT

    try:
        Path(python).relative_to(venv_dir)
    except ValueError:
        pass
    else:
        print(
            f"{error} Error, the python executable would be deleted!",
            "Change it using the --python option or PIPX_DEFAULT_PYTHON environment variable.",
        )
        return EXIT_CODE_REINSTALL_INVALID_PYTHON

    venv = Venv(venv_dir, verbose=verbose, backend=backend, env_backend=env_backend)
    venv.check_upgrade_shared_libs(
        pip_args=venv.pipx_metadata.main_package.pip_args, verbose=verbose, force_upgrade=force_reinstall_shared_libs
    )

    if venv.pipx_metadata.main_package.package_or_url is not None:
        package_or_url = venv.pipx_metadata.main_package.package_or_url
    else:
        package_or_url = venv.main_package_name

    if venv.pipx_metadata.main_package.pinned:
        raise PipxError(f"{error} Package {venv_dir} is pinned. Run `pipx unpin {venv_dir.name}` to unpin it first.")

    old_resource_paths = _get_reinstall_resource_paths(venv, local_bin_dir, local_man_dir)
    original_venv_dir = venv_dir
    reinstall_backup_dir = _create_reinstall_backup(venv_dir)
    print(f"uninstalled {venv.name}! {stars}")

    # in case legacy original dir name
    venv_dir = venv_dir.with_name(canonicalize_name(venv_dir.name))

    try:
        # install main package first
        install(
            venv_dir,
            [venv.main_package_name],
            [package_or_url],
            local_bin_dir,
            local_man_dir,
            python,
            venv.pipx_metadata.main_package.pip_args,
            venv.pipx_metadata.venv_args,
            verbose,
            force=True,
            reinstall=True,
            include_dependencies=venv.pipx_metadata.main_package.include_dependencies,
            preinstall_packages=[],
            suffix=venv.pipx_metadata.main_package.suffix,
            python_flag_passed=python_flag_passed,
            backend=backend or venv.pipx_metadata.backend,
            env_backend=env_backend,
        )

        # now install injected packages
        for injected_name, injected_package in venv.pipx_metadata.injected_packages.items():
            if injected_package.package_or_url is None:
                # This should never happen, but package_or_url is type
                #   Optional[str] so mypy thinks it could be None
                raise PipxError(f"Internal Error injecting package {injected_package} into {venv.name}")
            inject_dep(
                venv_dir,
                injected_name,
                injected_package.package_or_url,
                injected_package.pip_args,
                verbose=verbose,
                include_apps=injected_package.include_apps,
                include_dependencies=injected_package.include_dependencies,
                force=True,
                backend=backend or venv.pipx_metadata.backend,
                env_backend=env_backend,
            )

        new_resource_paths = _get_expected_reinstall_resource_paths(
            Venv(venv_dir, verbose=verbose), local_bin_dir, local_man_dir
        )
        _remove_stale_reinstall_resources(old_resource_paths - new_resource_paths)
    except (Exception, KeyboardInterrupt):
        _restore_reinstall_backup(venv_dir, original_venv_dir, reinstall_backup_dir)
        print(f"{error} Reinstall failed; restored {venv.name}.", file=sys.stderr)
        raise
    else:
        rmdir(reinstall_backup_dir)

    # Any failure to install will raise PipxError, otherwise success
    return EXIT_CODE_OK


def reinstall_all(
    venv_container: VenvContainer,
    local_bin_dir: Path,
    local_man_dir: Path,
    python: str,
    verbose: bool,
    *,
    skip: Sequence[str],
    python_flag_passed: bool = False,
    backend: str | None = None,
    env_backend: str | None = None,
) -> ExitCode:
    """Returns pipx exit code."""
    failed: list[str] = []
    reinstalled: list[str] = []

    # iterate on all packages and reinstall them
    # for the first one, we also trigger
    # a reinstall of shared libs beforehand
    first_reinstall = True
    for venv_dir in venv_container.iter_venv_dirs():
        if venv_dir.name in skip:
            continue
        try:
            reinstall(
                venv_dir=venv_dir,
                local_bin_dir=local_bin_dir,
                local_man_dir=local_man_dir,
                python=python,
                verbose=verbose,
                force_reinstall_shared_libs=first_reinstall,
                python_flag_passed=python_flag_passed,
                backend=backend,
                env_backend=env_backend,
            )
        except PipxError as e:
            print(e, file=sys.stderr)
            failed.append(venv_dir.name)
        else:
            first_reinstall = False
            reinstalled.append(venv_dir.name)
    if len(reinstalled) == 0:
        print(f"No packages reinstalled after running 'pipx reinstall-all' {sleep}")
    if len(failed) > 0:
        raise PipxError(f"The following package(s) failed to reinstall: {', '.join(failed)}")
    # Any failure to install will raise PipxError, otherwise success
    return EXIT_CODE_OK


__all__ = [
    "reinstall",
    "reinstall_all",
]
