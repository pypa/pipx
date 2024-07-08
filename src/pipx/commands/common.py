import logging
import os
import shlex
import shutil
import sys
import tempfile
import time
from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory
from typing import Dict, List, Optional, Set, Tuple

import userpath  # type: ignore[import-not-found]
from packaging.utils import canonicalize_name

from pipx import paths
from pipx.colors import bold, red
from pipx.constants import MAN_SECTIONS, WINDOWS
from pipx.emojis import hazard, stars
from pipx.package_specifier import parse_specifier_for_install, valid_pypi_name
from pipx.pipx_metadata_file import PackageInfo
from pipx.util import PipxError, mkdir, pipx_wrap, rmdir, safe_unlink
from pipx.venv import Venv

logger = logging.getLogger(__name__)


class VenvProblems:
    def __init__(
        self,
        bad_venv_name: bool = False,
        invalid_interpreter: bool = False,
        missing_metadata: bool = False,
        not_installed: bool = False,
    ) -> None:
        self.bad_venv_name = bad_venv_name
        self.invalid_interpreter = invalid_interpreter
        self.missing_metadata = missing_metadata
        self.not_installed = not_installed

    def any_(self) -> bool:
        return any(self.__dict__.values())

    def or_(self, venv_problems: "VenvProblems") -> None:
        for attribute in self.__dict__:
            setattr(
                self,
                attribute,
                getattr(self, attribute) or getattr(venv_problems, attribute),
            )


def expose_resources_globally(
    resource_type: str,
    local_resource_dir: Path,
    paths: List[Path],
    *,
    force: bool,
    suffix: str = "",
) -> None:
    for path in paths:
        src = path.resolve()
        if resource_type == "man":
            dest_dir = local_resource_dir / src.parent.name
        else:
            dest_dir = local_resource_dir
        if not dest_dir.is_dir():
            mkdir(dest_dir)
        if not can_symlink(dest_dir):
            _copy_package_resource(dest_dir, path, suffix=suffix)
        else:
            _symlink_package_resource(
                dest_dir,
                path,
                force=force,
                suffix=suffix,
                executable=(resource_type == "app"),
            )


_can_symlink_cache: Dict[Path, bool] = {}


def can_symlink(local_resource_dir: Path) -> bool:
    if not WINDOWS:
        # Technically, even on Unix this depends on the filesystem
        return True

    if local_resource_dir not in _can_symlink_cache:
        with TemporaryDirectory(dir=local_resource_dir) as d:
            p = Path(d)
            target = p / "a"
            target.touch()
            lnk = p / "b"
            try:
                lnk.symlink_to(target)
                _can_symlink_cache[local_resource_dir] = True
            except (OSError, NotImplementedError):
                _can_symlink_cache[local_resource_dir] = False

    return _can_symlink_cache[local_resource_dir]


def _copy_package_resource(dest_dir: Path, path: Path, suffix: str = "") -> None:
    src = path.resolve()
    name = src.name
    dest = Path(dest_dir / add_suffix(name, suffix))
    if not dest.parent.is_dir():
        mkdir(dest.parent)
    if dest.exists():
        logger.warning(f"{hazard}  Overwriting file {dest!s} with {src!s}")
        safe_unlink(dest)
    if src.exists():
        shutil.copy(src, dest)


def _symlink_package_resource(
    dest_dir: Path,
    path: Path,
    *,
    force: bool,
    suffix: str = "",
    executable: bool = False,
) -> None:
    name_suffixed = add_suffix(path.name, suffix)
    symlink_path = Path(dest_dir / name_suffixed)

    if not symlink_path.parent.is_dir():
        mkdir(symlink_path.parent)

    if force:
        logger.info(f"Force is true. Removing {symlink_path!s}.")
        try:
            symlink_path.unlink()
        except FileNotFoundError:
            pass
        except IsADirectoryError:
            rmdir(symlink_path)

    exists = symlink_path.exists()
    is_symlink = symlink_path.is_symlink()
    if exists:
        if symlink_path.samefile(path):
            logger.info(f"Same path {symlink_path!s} and {path!s}")
        else:
            logger.warning(
                pipx_wrap(
                    f"""
                    {hazard}  File exists at {symlink_path!s} and points
                    to {symlink_path.resolve()}, not {path!s}. Not
                    modifying.
                    """,
                    subsequent_indent=" " * 4,
                )
            )
        return
    if is_symlink and not exists:
        logger.info(f"Removing existing symlink {symlink_path!s} since it pointed non-existent location")
        symlink_path.unlink()

    if executable:
        existing_executable_on_path = which(name_suffixed)
    else:
        existing_executable_on_path = None
    symlink_path.symlink_to(path)

    if executable and existing_executable_on_path:
        logger.warning(
            pipx_wrap(
                f"""
                {hazard}  Note: {name_suffixed} was already on your
                PATH at {existing_executable_on_path}
                """,
                subsequent_indent=" " * 4,
            )
        )


def venv_health_check(venv: Venv, package_name: Optional[str] = None) -> Tuple[VenvProblems, str]:
    venv_dir = venv.root
    python_path = venv.python_path.resolve()

    if package_name is None:
        package_name = venv.main_package_name

    if not python_path.is_file():
        return (
            VenvProblems(invalid_interpreter=True),
            f"   package {red(bold(venv_dir.name))} has invalid interpreter {python_path!s}\r{hazard}",
        )
    if not venv.package_metadata:
        return (
            VenvProblems(missing_metadata=True),
            f"   package {red(bold(venv_dir.name))} has missing internal pipx metadata.\r{hazard}",
        )
    if venv_dir.name != canonicalize_name(venv_dir.name):
        return (
            VenvProblems(bad_venv_name=True),
            f"   package {red(bold(venv_dir.name))} needs its internal data updated.\r{hazard}",
        )
    if venv.package_metadata[package_name].package_version == "":
        return (
            VenvProblems(not_installed=True),
            f"   package {red(bold(package_name))} {red('is not installed')} in the venv {venv_dir.name}\r{hazard}",
        )
    return (VenvProblems(), "")


def get_venv_summary(
    venv_dir: Path,
    *,
    package_name: Optional[str] = None,
    new_install: bool = False,
    include_injected: bool = False,
) -> Tuple[str, VenvProblems]:
    venv = Venv(venv_dir)

    if package_name is None:
        package_name = venv.main_package_name

    (venv_problems, warning_message) = venv_health_check(venv, package_name)
    if venv_problems.any_():
        return (warning_message, venv_problems)

    package_metadata = venv.package_metadata[package_name]
    apps = package_metadata.apps
    man_pages = package_metadata.man_pages
    if package_metadata.include_dependencies:
        apps += package_metadata.apps_of_dependencies
        man_pages += package_metadata.man_pages_of_dependencies

    exposed_app_paths = get_exposed_paths_for_package(
        venv.bin_path,
        paths.ctx.bin_dir,
        [add_suffix(app, package_metadata.suffix) for app in apps],
    )
    exposed_binary_names = sorted(p.name for p in exposed_app_paths)
    unavailable_binary_names = sorted(
        {add_suffix(name, package_metadata.suffix) for name in package_metadata.apps} - set(exposed_binary_names)
    )
    exposed_man_paths = set()
    for man_section in MAN_SECTIONS:
        exposed_man_paths |= get_exposed_man_paths_for_package(
            venv.man_path / man_section,
            paths.ctx.man_dir / man_section,
            man_pages,
        )
    exposed_man_pages = sorted(str(Path(p.parent.name) / p.name) for p in exposed_man_paths)
    unavailable_man_pages = sorted(set(package_metadata.man_pages) - set(exposed_man_pages))
    # The following is to satisfy mypy that python_version is str and not
    #   Optional[str]
    python_version = venv.pipx_metadata.python_version if venv.pipx_metadata.python_version is not None else ""
    source_interpreter = venv.pipx_metadata.source_interpreter
    is_standalone = (
        str(source_interpreter).startswith(str(paths.ctx.standalone_python_cachedir.resolve()))
        if source_interpreter
        else False
    )
    return (
        _get_list_output(
            python_version,
            is_standalone,
            package_metadata.package_version,
            package_name,
            new_install,
            exposed_binary_names,
            unavailable_binary_names,
            exposed_man_pages,
            unavailable_man_pages,
            venv.pipx_metadata.injected_packages if include_injected else None,
            suffix=package_metadata.suffix,
        ),
        venv_problems,
    )


def get_exposed_paths_for_package(
    venv_resource_path: Path,
    local_resource_dir: Path,
    package_resource_names: Optional[List[str]] = None,
) -> Set[Path]:
    # package_binary_names is used only if local_bin_path cannot use symlinks.
    # It is necessary for non-symlink systems to return valid app_paths.
    if package_resource_names is None:
        package_resource_names = []

    if not local_resource_dir.exists():
        return set()

    symlinks = set()
    for b in local_resource_dir.iterdir():
        try:
            # sometimes symlinks can resolve to a file of a different name
            # (in the case of ansible for example) so checking the resolved paths
            # is not a reliable way to determine if the symlink exists.
            # We always use the stricter check on non-Windows systems. On
            # Windows, we use a less strict check if we don't have a symlink.
            is_same_file = False
            if can_symlink(local_resource_dir) and b.is_symlink():
                is_same_file = b.resolve().parent.samefile(venv_resource_path)
            elif not can_symlink(local_resource_dir):
                is_same_file = b.name in package_resource_names

            if is_same_file:
                symlinks.add(b)

        except FileNotFoundError:
            pass
    return symlinks


def get_exposed_man_paths_for_package(
    venv_man_path: Path,
    local_man_dir: Path,
    package_man_pages: Optional[List[str]] = None,
) -> Set[Path]:
    man_section = venv_man_path.name
    prefix = man_section + os.sep
    return get_exposed_paths_for_package(
        venv_man_path,
        local_man_dir,
        [
            (name[len(prefix) :] if name.startswith(prefix) else name)
            for name in package_man_pages or []
            if name.startswith(prefix)
        ],
    )


def _get_list_output(
    python_version: str,
    python_is_standalone: bool,
    package_version: str,
    package_name: str,
    new_install: bool,
    exposed_binary_names: List[str],
    unavailable_binary_names: List[str],
    exposed_man_pages: List[str],
    unavailable_man_pages: List[str],
    injected_packages: Optional[Dict[str, PackageInfo]] = None,
    suffix: str = "",
) -> str:
    output = []
    suffix = f" ({bold(shlex.quote(package_name + suffix))})" if suffix else ""
    output.append(
        f"  {'installed' if new_install else ''} package {bold(shlex.quote(package_name))}"
        f" {bold(package_version)}{suffix}, installed using {python_version}"
        + (" (standalone)" if python_is_standalone else "")
    )

    if new_install and (exposed_binary_names or unavailable_binary_names):
        output.append("  These apps are now globally available")
    output.extend(f"    - {name}" for name in exposed_binary_names)
    output.extend(
        f"    - {red(name)} (symlink missing or pointing to unexpected location)" for name in unavailable_binary_names
    )
    if new_install and (exposed_man_pages or unavailable_man_pages):
        output.append("  These manual pages are now globally available")
    output.extend(f"    - {name}" for name in exposed_man_pages)
    output.extend(
        f"    - {red(name)} (symlink missing or pointing to unexpected location)" for name in unavailable_man_pages
    )
    if injected_packages:
        output.append("    Injected Packages:")
        output.extend(f"      - {name} {injected_packages[name].package_version}" for name in injected_packages)
    return "\n".join(output)


def package_name_from_spec(package_spec: str, python: str, *, pip_args: List[str], verbose: bool) -> str:
    start_time = time.time()

    # shortcut if valid PyPI name
    pypi_name = valid_pypi_name(package_spec)
    if pypi_name is not None:
        # NOTE: if pypi name and installed package name differ, this means pipx
        #       will use the pypi name
        package_name = pypi_name
        logger.info(f"Determined package name: {package_name}")
        logger.info(f"Package name determined in {time.time()-start_time:.1f}s")
        return package_name

    # check syntax and clean up spec and pip_args
    (package_spec, pip_args) = parse_specifier_for_install(package_spec, pip_args)

    with tempfile.TemporaryDirectory() as temp_venv_dir:
        venv = Venv(Path(temp_venv_dir), python=python, verbose=verbose)
        venv.create_venv(venv_args=[], pip_args=[])
        package_name = venv.install_package_no_deps(package_or_url=package_spec, pip_args=pip_args)

    logger.info(f"Package name determined in {time.time()-start_time:.1f}s")
    return package_name


def run_post_install_actions(
    venv: Venv,
    package_name: str,
    local_bin_dir: Path,
    local_man_dir: Path,
    venv_dir: Path,
    include_dependencies: bool,
    *,
    force: bool,
) -> None:
    package_metadata = venv.package_metadata[package_name]

    display_name = f"{package_name}{package_metadata.suffix}"

    if (
        not venv.main_package_name == package_name
        and venv.package_metadata[venv.main_package_name].suffix == package_metadata.suffix
    ):
        package_name = display_name

    if not package_metadata.apps:
        if not package_metadata.apps_of_dependencies:
            if venv.safe_to_remove():
                venv.remove_venv()
            raise PipxError(
                f"""
                No apps associated with package {display_name} or its
                dependencies. If you are attempting to install a library, pipx
                should not be used. Consider using pip or a similar tool instead.
                """
            )
        if package_metadata.apps_of_dependencies and not include_dependencies:
            for (
                dep,
                dependent_apps,
            ) in package_metadata.app_paths_of_dependencies.items():
                print(f"Note: Dependent package '{dep}' contains {len(dependent_apps)} apps")
                for app in dependent_apps:
                    print(f"  - {app.name}")
            if venv.safe_to_remove():
                venv.remove_venv()
            raise PipxError(
                f"""
                No apps associated with package {display_name}. Try again
                with '--include-deps' to include apps of dependent packages,
                which are listed above. If you are attempting to install a
                library, pipx should not be used. Consider using pip or a
                similar tool instead.
                """
            )

    expose_resources_globally(
        "app",
        local_bin_dir,
        package_metadata.app_paths,
        force=force,
        suffix=package_metadata.suffix,
    )
    expose_resources_globally("man", local_man_dir, package_metadata.man_paths, force=force)

    if include_dependencies:
        for app_paths in package_metadata.app_paths_of_dependencies.values():
            expose_resources_globally(
                "app",
                local_bin_dir,
                app_paths,
                force=force,
                suffix=package_metadata.suffix,
            )
        for man_paths in package_metadata.man_paths_of_dependencies.values():
            expose_resources_globally("man", local_man_dir, man_paths, force=force)

    package_summary, _ = get_venv_summary(venv_dir, package_name=package_name, new_install=True)
    print(package_summary)
    warn_if_not_on_path(local_bin_dir)
    print(f"done! {stars}", file=sys.stderr)


def warn_if_not_on_path(local_bin_dir: Path) -> None:
    if not userpath.in_current_path(str(local_bin_dir)):
        logger.warning(
            pipx_wrap(
                f"""
                {hazard}  Note: '{local_bin_dir}' is not on your PATH
                environment variable. These apps will not be globally
                accessible until your PATH is updated. Run `pipx ensurepath` to
                automatically add it, or manually modify your PATH in your
                shell's config file (e.g. ~/.bashrc).
                """,
                subsequent_indent=" " * 4,
            )
        )


def add_suffix(name: str, suffix: str) -> str:
    """Add suffix to app."""

    app = Path(name)
    return f"{app.stem}{suffix}{app.suffix}"
