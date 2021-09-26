import logging
import shlex
import shutil
import sys
import tempfile
import time
from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory
from typing import Dict, List, Optional, Set, Tuple

import userpath  # type: ignore
from packaging.utils import canonicalize_name

from pipx import constants
from pipx.colors import bold, red
from pipx.constants import WINDOWS
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


def expose_apps_globally(
    local_bin_dir: Path, app_paths: List[Path], *, force: bool, suffix: str = ""
) -> None:
    if not can_symlink(local_bin_dir):
        _copy_package_apps(local_bin_dir, app_paths, suffix=suffix)
    else:
        _symlink_package_apps(local_bin_dir, app_paths, force=force, suffix=suffix)


_can_symlink_cache: Dict[Path, bool] = {}


def can_symlink(local_bin_dir: Path) -> bool:

    if not WINDOWS:
        # Technically, even on Unix this depends on the filesystem
        return True

    if local_bin_dir not in _can_symlink_cache:
        with TemporaryDirectory(dir=local_bin_dir) as d:
            p = Path(d)
            target = p / "a"
            target.touch()
            lnk = p / "b"
            try:
                lnk.symlink_to(target)
                _can_symlink_cache[local_bin_dir] = True
            except (OSError, NotImplementedError):
                _can_symlink_cache[local_bin_dir] = False

    return _can_symlink_cache[local_bin_dir]


def _copy_package_apps(
    local_bin_dir: Path, app_paths: List[Path], suffix: str = ""
) -> None:
    for src_unresolved in app_paths:
        src = src_unresolved.resolve()
        app = src.name
        dest = Path(local_bin_dir / add_suffix(app, suffix))
        if not dest.parent.is_dir():
            mkdir(dest.parent)
        if dest.exists():
            logger.warning(f"{hazard}  Overwriting file {str(dest)} with {str(src)}")
            safe_unlink(dest)
        if src.exists():
            shutil.copy(src, dest)


def _symlink_package_apps(
    local_bin_dir: Path, app_paths: List[Path], *, force: bool, suffix: str = ""
) -> None:
    for app_path in app_paths:
        app_name = app_path.name
        app_name_suffixed = add_suffix(app_name, suffix)
        symlink_path = Path(local_bin_dir / app_name_suffixed)
        if not symlink_path.parent.is_dir():
            mkdir(symlink_path.parent)

        if force:
            logger.info(f"Force is true. Removing {str(symlink_path)}.")
            try:
                symlink_path.unlink()
            except FileNotFoundError:
                pass
            except IsADirectoryError:
                rmdir(symlink_path)

        exists = symlink_path.exists()
        is_symlink = symlink_path.is_symlink()
        if exists:
            if symlink_path.samefile(app_path):
                logger.info(f"Same path {str(symlink_path)} and {str(app_path)}")
            else:
                logger.warning(
                    pipx_wrap(
                        f"""
                        {hazard}  File exists at {str(symlink_path)} and points
                        to {symlink_path.resolve()}, not {str(app_path)}. Not
                        modifying.
                        """,
                        subsequent_indent=" " * 4,
                    )
                )
            continue
        if is_symlink and not exists:
            logger.info(
                f"Removing existing symlink {str(symlink_path)} since it "
                "pointed non-existent location"
            )
            symlink_path.unlink()

        existing_executable_on_path = which(app_name_suffixed)
        symlink_path.symlink_to(app_path)

        if existing_executable_on_path:
            logger.warning(
                pipx_wrap(
                    f"""
                    {hazard}  Note: {app_name_suffixed} was already on your
                    PATH at {existing_executable_on_path}
                    """,
                    subsequent_indent=" " * 4,
                )
            )


def venv_health_check(
    venv: Venv, package_name: Optional[str] = None
) -> Tuple[VenvProblems, str]:
    venv_dir = venv.root
    python_path = venv.python_path.resolve()

    if package_name is None:
        package_name = venv.main_package_name

    if not python_path.is_file():
        return (
            VenvProblems(invalid_interpreter=True),
            f"   package {red(bold(venv_dir.name))} has invalid "
            f"interpreter {str(python_path)}\r{hazard}",
        )
    if not venv.package_metadata:
        return (
            VenvProblems(missing_metadata=True),
            f"   package {red(bold(venv_dir.name))} has missing "
            f"internal pipx metadata.\r{hazard}",
        )
    if venv_dir.name != canonicalize_name(venv_dir.name):
        return (
            VenvProblems(bad_venv_name=True),
            f"   package {red(bold(venv_dir.name))} needs its "
            f"internal data updated.\r{hazard}",
        )
    if venv.package_metadata[package_name].package_version == "":
        return (
            VenvProblems(not_installed=True),
            f"   package {red(bold(package_name))} {red('is not installed')} "
            f"in the venv {venv_dir.name}\r{hazard}",
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
    if package_metadata.include_dependencies:
        apps += package_metadata.apps_of_dependencies

    exposed_app_paths = get_exposed_app_paths_for_package(
        venv.bin_path,
        constants.LOCAL_BIN_DIR,
        [add_suffix(app, package_metadata.suffix) for app in apps],
    )
    exposed_binary_names = sorted(p.name for p in exposed_app_paths)
    unavailable_binary_names = sorted(
        {add_suffix(name, package_metadata.suffix) for name in package_metadata.apps}
        - set(exposed_binary_names)
    )
    # The following is to satisfy mypy that python_version is str and not
    #   Optional[str]
    python_version = (
        venv.pipx_metadata.python_version
        if venv.pipx_metadata.python_version is not None
        else ""
    )
    return (
        _get_list_output(
            python_version,
            package_metadata.package_version,
            package_name,
            new_install,
            exposed_binary_names,
            unavailable_binary_names,
            venv.pipx_metadata.injected_packages if include_injected else None,
            suffix=package_metadata.suffix,
        ),
        venv_problems,
    )


def get_exposed_app_paths_for_package(
    venv_bin_path: Path,
    local_bin_dir: Path,
    package_binary_names: Optional[List[str]] = None,
) -> Set[Path]:
    # package_binary_names is used only if local_bin_path cannot use symlinks.
    # It is necessary for non-symlink systems to return valid app_paths.
    if package_binary_names is None:
        package_binary_names = []

    bin_symlinks = set()
    for b in local_bin_dir.iterdir():
        try:
            # sometimes symlinks can resolve to a file of a different name
            # (in the case of ansible for example) so checking the resolved paths
            # is not a reliable way to determine if the symlink exists.
            # We always use the stricter check on non-Windows systems. On
            # Windows, we use a less strict check if we don't have a symlink.
            is_same_file = False
            if can_symlink(local_bin_dir) and b.is_symlink():
                is_same_file = b.resolve().parent.samefile(venv_bin_path)
            elif not can_symlink(local_bin_dir):
                is_same_file = b.name in package_binary_names

            if is_same_file:
                bin_symlinks.add(b)

        except FileNotFoundError:
            pass
    return bin_symlinks


def _get_list_output(
    python_version: str,
    package_version: str,
    package_name: str,
    new_install: bool,
    exposed_binary_names: List[str],
    unavailable_binary_names: List[str],
    injected_packages: Optional[Dict[str, PackageInfo]] = None,
    suffix: str = "",
) -> str:
    output = []
    suffix = f" ({bold(shlex.quote(package_name + suffix))})" if suffix else ""
    output.append(
        f"  {'installed' if new_install else ''} package {bold(shlex.quote(package_name))}"
        f" {bold(package_version)}{suffix}, installed using {python_version}"
    )

    if new_install and exposed_binary_names:
        output.append("  These apps are now globally available")
    for name in exposed_binary_names:
        output.append(f"    - {name}")
    for name in unavailable_binary_names:
        output.append(
            f"    - {red(name)} (symlink missing or pointing to unexpected location)"
        )
    if injected_packages:
        output.append("    Injected Packages:")
        for name in injected_packages:
            output.append(f"      - {name} {injected_packages[name].package_version}")
    return "\n".join(output)


def package_name_from_spec(
    package_spec: str, python: str, *, pip_args: List[str], verbose: bool
) -> str:
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
        package_name = venv.install_package_no_deps(
            package_or_url=package_spec, pip_args=pip_args
        )

    logger.info(f"Package name determined in {time.time()-start_time:.1f}s")
    return package_name


def run_post_install_actions(
    venv: Venv,
    package_name: str,
    local_bin_dir: Path,
    venv_dir: Path,
    include_dependencies: bool,
    *,
    force: bool,
) -> None:
    package_metadata = venv.package_metadata[package_name]

    display_name = f"{package_name}{package_metadata.suffix}"

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
                print(
                    f"Note: Dependent package '{dep}' contains {len(dependent_apps)} apps"
                )
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
                similar tool instead."
                """
            )

    expose_apps_globally(
        local_bin_dir,
        package_metadata.app_paths,
        force=force,
        suffix=package_metadata.suffix,
    )

    if include_dependencies:
        for _, app_paths in package_metadata.app_paths_of_dependencies.items():
            expose_apps_globally(
                local_bin_dir, app_paths, force=force, suffix=package_metadata.suffix
            )

    package_summary, _ = get_venv_summary(
        venv_dir, package_name=package_name, new_install=True
    )
    print(package_summary)
    warn_if_not_on_path(local_bin_dir)
    print(f"done! {stars}", file=sys.stderr)


def warn_if_not_on_path(local_bin_dir: Path) -> None:
    if not userpath.in_current_path(str(local_bin_dir)):
        logger.warning(
            pipx_wrap(
                f"""
                {hazard}  Note: {str(local_bin_dir)!r} is not on your PATH
                environment variable. These apps will not be globally
                accessible until your PATH is updated. Run `pipx ensurepath` to
                automatically add it, or manually modify your PATH in your
                shell's config file (i.e. ~/.bashrc).
                """,
                subsequent_indent=" " * 4,
            )
        )


def add_suffix(name: str, suffix: str) -> str:
    """Add suffix to app."""

    app = Path(name)
    return f"{app.stem}{suffix}{app.suffix}"
