from __future__ import annotations

import filecmp
import logging
import re
import shlex
import shutil
import tempfile
import time
from pathlib import Path
from re import Pattern
from shutil import which
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Final

import userpath
from packaging.utils import canonicalize_name

from pipx import paths
from pipx.colors import bold, red
from pipx.constants import COMPLETION_SECTIONS, MAN_SECTIONS, WINDOWS
from pipx.emojis import hazard, stars
from pipx.package_specifier import parse_specifier_for_install, valid_pypi_name
from pipx.result import OutputMessage, OutputStream
from pipx.util import PipxError, mkdir, pipx_wrap, rmdir, safe_unlink
from pipx.venv import Venv

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from pipx.pipx_metadata_file import PackageInfo

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


class VenvProblems:
    def __init__(
        self,
        *,
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

    def or_(self, venv_problems: VenvProblems) -> None:
        for attribute in self.__dict__:
            setattr(
                self,
                attribute,
                getattr(self, attribute) or getattr(venv_problems, attribute),
            )


def expose_resources_globally(
    resource_type: str,
    local_resource_dir: Path,
    paths: list[Path],
    *,
    force: bool,
    suffix: str = "",
) -> list[Path]:
    collisions: Final[list[Path]] = []
    for path in paths:
        if resource_type == "app":
            _add_ignore_environment_to_python_shebang(path)
        src = path.resolve()
        if resource_type == "man":
            dest_dir = local_resource_dir / src.parent.name
        elif resource_type == "completion":
            # a completion section is two levels deep, such as bash-completion/completions
            dest_dir = local_resource_dir / src.parent.parent.name / src.parent.name
        else:
            dest_dir = local_resource_dir
        if not dest_dir.is_dir():
            mkdir(dest_dir)
        if not can_symlink(dest_dir):
            collision = _copy_package_resource(dest_dir, path, force=force, suffix=suffix)
        else:
            collision = _symlink_package_resource(
                dest_dir,
                path,
                force=force,
                suffix=suffix,
                executable=(resource_type == "app"),
            )
        if collision is not None:
            collisions.append(collision)
    return collisions


def expose_package_resources(
    package_metadata: PackageInfo,
    local_bin_dir: Path,
    local_man_dir: Path,
    *,
    force: bool,
) -> list[Path]:
    collisions: Final[list[Path]] = []
    if app_paths := package_metadata.app_paths_to_expose:
        collisions.extend(
            expose_resources_globally("app", local_bin_dir, app_paths, force=force, suffix=package_metadata.suffix)
        )
    if man_paths := package_metadata.man_paths_to_expose:
        collisions.extend(expose_resources_globally("man", local_man_dir, man_paths, force=force))
    if completion_paths := package_metadata.completion_paths_to_expose:
        # the script names the command it completes, so a suffix here would point the shell at a command that is gone
        collisions.extend(
            expose_resources_globally("completion", paths.ctx.completion_dir, completion_paths, force=force)
        )
    return collisions


_can_symlink_cache: dict[Path, bool] = {}


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


def _add_ignore_environment_to_python_shebang(path: Path) -> None:
    if WINDOWS or not path.is_file():
        return

    try:
        data = path.read_bytes()
    except OSError:
        return

    first_line, separator, rest = data.partition(b"\n")
    if not first_line.startswith(b"#!"):
        return

    interpreter = first_line[2:]
    if interpreter.endswith(b" -E"):
        return
    if b"python" not in interpreter.lower() or b" " in interpreter or b"\t" in interpreter:
        return

    path.write_bytes(first_line + b" -E" + separator + rest)


def _copy_package_resource(dest_dir: Path, path: Path, *, force: bool, suffix: str = "") -> Path | None:
    src = path.resolve()
    name = src.name
    dest = Path(dest_dir / add_suffix(name, suffix))
    if not dest.parent.is_dir():
        mkdir(dest.parent)
    if dest.exists():
        if filecmp.cmp(dest, src, shallow=False):
            return None
        if not force:
            _LOGGER.warning("%s  File exists at %s and does not match %s. Not modifying.", hazard, dest, src)
            return dest
        _LOGGER.warning("%s  Overwriting file %s with %s", hazard, dest, src)
        safe_unlink(dest)
    if src.exists():
        shutil.copy(src, dest)
    return None


def _symlink_package_resource(
    dest_dir: Path,
    path: Path,
    *,
    force: bool,
    suffix: str = "",
    executable: bool = False,
) -> Path | None:
    name_suffixed = add_suffix(path.name, suffix)
    symlink_path = Path(dest_dir / name_suffixed)

    if not symlink_path.parent.is_dir():
        mkdir(symlink_path.parent)

    if force:
        _LOGGER.info("Force is true. Removing %s.", symlink_path)
        try:
            symlink_path.unlink()
        except (FileNotFoundError, RuntimeError):
            pass
        except IsADirectoryError:
            rmdir(symlink_path)

    exists = symlink_path.exists()
    is_symlink = symlink_path.is_symlink()
    if exists:
        if symlink_path.samefile(path):
            _LOGGER.info("Same path %s and %s", symlink_path, path)
            return None
        _LOGGER.warning(
            pipx_wrap(
                f"""
                {hazard}  File exists at {symlink_path!s} and points
                to {symlink_path.resolve()}, not {path!s}. Not
                modifying.
                """,
                subsequent_indent=" " * 4,
            )
        )
        return symlink_path
    if is_symlink and not exists:
        _LOGGER.info("Removing existing symlink %s since it pointed non-existent location", symlink_path)
        symlink_path.unlink()

    existing_executable_on_path = which(name_suffixed) if executable else None
    symlink_path.symlink_to(path)

    if executable and existing_executable_on_path:
        _LOGGER.warning(
            pipx_wrap(
                f"""
                {hazard}  Note: {name_suffixed} was already on your
                PATH at {existing_executable_on_path}
                """,
                subsequent_indent=" " * 4,
            )
        )
    return None


def venv_health_check(venv: Venv, package_name: str | None = None) -> tuple[VenvProblems, str]:
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
    if not venv.package_metadata[package_name].package_version:
        return (
            VenvProblems(not_installed=True),
            f"   package {red(bold(package_name))} {red('is not installed')} in the venv {venv_dir.name}\r{hazard}",
        )
    return (VenvProblems(), "")


def _get_exposed_resource_names(
    venv: Venv,
    package_metadata: PackageInfo,
    *,
    new_install: bool,
) -> tuple[list[str], list[str], list[str], list[str]]:
    resource_packages: Final[tuple[PackageInfo, ...]] = (
        (package_metadata,)
        if new_install
        else tuple(metadata for metadata in venv.package_metadata.values() if metadata.include_apps)
    )
    app_paths: Final[dict[str, list[Path]]] = group_resource_paths(
        (add_suffix(path.name, metadata.suffix), path)
        for metadata in resource_packages
        for path in metadata.app_paths_to_expose
    )
    exposed_app_paths = get_exposed_paths_for_package(venv.bin_path, paths.ctx.bin_dir, app_paths)
    exposed_binary_names = sorted(path.name for path in exposed_app_paths)
    unavailable_binary_names = sorted(
        {add_suffix(name, package_metadata.suffix) for name in package_metadata.apps} - set(exposed_binary_names)
    )
    exposed_man_paths = set()
    man_paths: Final[list[Path]] = [path for metadata in resource_packages for path in metadata.man_paths_to_expose]
    for man_section in MAN_SECTIONS:
        exposed_man_paths |= get_exposed_man_paths_for_package(
            venv.man_path / man_section,
            paths.ctx.man_dir / man_section,
            man_paths,
        )
    exposed_man_pages = sorted(str(Path(path.parent.name) / path.name) for path in exposed_man_paths)
    unavailable_man_pages = sorted(set(package_metadata.man_pages) - set(exposed_man_pages))
    return exposed_binary_names, unavailable_binary_names, exposed_man_pages, unavailable_man_pages


def get_venv_summary(
    venv_dir: Path,
    *,
    package_name: str | None = None,
    new_install: bool = False,
    include_injected: bool = False,
) -> tuple[str, VenvProblems]:
    venv = Venv(venv_dir)

    if package_name is None:
        package_name = venv.main_package_name

    (venv_problems, warning_message) = venv_health_check(venv, package_name)
    if venv_problems.any_():
        return (warning_message, venv_problems)

    package_metadata: Final[PackageInfo] = venv.package_metadata[package_name]
    exposed_binary_names, unavailable_binary_names, exposed_man_pages, unavailable_man_pages = (
        _get_exposed_resource_names(venv, package_metadata, new_install=new_install)
        if venv.pipx_metadata.exposure_enabled
        else ([], [], [], [])
    )
    # narrow python_version to a str for mypy; the metadata types it as optional
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
            package_metadata.package_version,
            package_name,
            python_is_standalone=is_standalone,
            new_install=new_install,
            exposed_binary_names=exposed_binary_names,
            unavailable_binary_names=unavailable_binary_names,
            exposed_man_pages=exposed_man_pages,
            unavailable_man_pages=unavailable_man_pages,
            injected_packages=venv.pipx_metadata.injected_packages if include_injected else None,
            suffix=package_metadata.suffix,
            exposure_enabled=venv.pipx_metadata.exposure_enabled,
        ),
        venv_problems,
    )


def get_exposed_paths_for_package(
    venv_resource_path: Path,
    local_resource_dir: Path,
    package_resource_paths: Mapping[str, Sequence[Path]] | None = None,
) -> set[Path]:
    if not local_resource_dir.exists():
        return set()

    return {
        resource_path
        for resource_path in local_resource_dir.iterdir()
        if _resource_belongs_to_venv(resource_path, venv_resource_path, local_resource_dir, package_resource_paths)
    }


def _resource_belongs_to_venv(
    resource_path: Path,
    venv_resource_path: Path,
    local_resource_dir: Path,
    package_resource_paths: Mapping[str, Sequence[Path]] | None,
) -> bool:
    try:
        # Some apps expose symlinks whose names differ from their targets, so resolved paths cannot identify them.
        # Windows setups without symlink support fall back to package resource names.
        if can_symlink(local_resource_dir) and resource_path.is_symlink():
            return resource_path.resolve().parent.samefile(venv_resource_path)
        if not can_symlink(local_resource_dir):
            sources = package_resource_paths.get(resource_path.name, ()) if package_resource_paths is not None else ()
            return any(source.is_file() and filecmp.cmp(resource_path, source, shallow=False) for source in sources)
    except (FileNotFoundError, RuntimeError):
        return False
    return False


def get_exposed_man_paths_for_package(
    venv_man_path: Path,
    local_man_dir: Path,
    package_man_paths: Sequence[Path] = (),
) -> set[Path]:
    man_section = venv_man_path.name
    return get_exposed_paths_for_package(
        venv_man_path,
        local_man_dir,
        group_resource_paths((path.name, path) for path in package_man_paths if path.parent.name == man_section),
    )


def group_resource_paths(resource_paths: Iterable[tuple[str, Path]]) -> dict[str, list[Path]]:
    grouped: dict[str, list[Path]] = {}
    for name, path in resource_paths:
        grouped.setdefault(name, []).append(path)
    return grouped


def _get_list_output(  # noqa: PLR0913  # flat rendering inputs; a wrapper struct would only add indirection
    python_version: str,
    package_version: str,
    package_name: str,
    *,
    python_is_standalone: bool,
    new_install: bool,
    exposed_binary_names: list[str],
    unavailable_binary_names: list[str],
    exposed_man_pages: list[str],
    unavailable_man_pages: list[str],
    injected_packages: dict[str, PackageInfo] | None = None,
    suffix: str = "",
    exposure_enabled: bool,
) -> str:
    output = []
    suffix = f" ({bold(shlex.quote(package_name + suffix))})" if suffix else ""
    output.append(
        f"  {'installed' if new_install else ''} package {bold(shlex.quote(package_name))}"
        f" {bold(package_version)}{suffix}, installed using {python_version}"
        + (" (standalone)" if python_is_standalone else "")
    )

    if not exposure_enabled:
        output.append("    apps and manual pages are not exposed")
    if new_install and (exposed_binary_names or unavailable_binary_names):
        output.append("  These apps are now available")
    output.extend(f"    - {name}" for name in exposed_binary_names)
    output.extend(
        f"    - {red(name)} (symlink missing or pointing to unexpected location)" for name in unavailable_binary_names
    )
    if new_install and (exposed_man_pages or unavailable_man_pages):
        output.append("  These manual pages are now available")
    output.extend(f"    - {name}" for name in exposed_man_pages)
    output.extend(
        f"    - {red(name)} (symlink missing or pointing to unexpected location)" for name in unavailable_man_pages
    )
    if injected_packages:
        output.append("    Injected Packages:")
        output.extend(f"      - {name} {injected_packages[name].package_version}" for name in injected_packages)
    return "\n".join(output)


def package_name_from_spec(  # noqa: PLR0913  # resolver inputs are independent scalars, not a cohesive struct
    package_spec: str,
    python: str,
    *,
    pip_args: list[str],
    verbose: bool,
    backend: str | None = None,
    env_backend: str | None = None,
    cooldown_days: int | None = None,
) -> str:
    start_time = time.time()

    # shortcut if valid PyPI name
    pypi_name = valid_pypi_name(package_spec)
    if pypi_name is not None:
        # NOTE: if pypi name and installed package name differ, this means pipx
        #       will use the pypi name
        package_name = pypi_name
        _LOGGER.info("Determined package name: %s", package_name)
        _LOGGER.info("Package name determined in %.1fs", time.time() - start_time)
        return package_name

    # check syntax and clean up spec and pip_args
    (package_spec, pip_args) = parse_specifier_for_install(package_spec, pip_args)

    with tempfile.TemporaryDirectory() as temp_venv_dir:
        venv = Venv(Path(temp_venv_dir), python=python, verbose=verbose, backend=backend, env_backend=env_backend)
        venv.create_venv(venv_args=[], pip_args=[])
        package_name = venv.install_package_no_deps(
            package_or_url=package_spec,
            pip_args=pip_args,
            cooldown_days=cooldown_days,
        )

    _LOGGER.info("Package name determined in %.1fs", time.time() - start_time)
    return package_name


def run_post_install_actions(  # noqa: PLR0913  # post-install needs venv, both resource dirs, and the venv dir
    venv: Venv,
    package_name: str,
    local_bin_dir: Path,
    local_man_dir: Path,
    venv_dir: Path,
    *,
    force: bool,
    previous_resource_paths: set[Path],
) -> tuple[OutputMessage, ...]:
    package_metadata = venv.package_metadata[package_name]

    display_name = f"{package_name}{package_metadata.suffix}"

    if (
        venv.main_package_name != package_name
        and venv.package_metadata[venv.main_package_name].suffix == package_metadata.suffix
    ):
        package_name = display_name

    if not package_metadata.apps:
        library_name = package_metadata.package or package_name
        library_guidance = (
            "`pipx install` requires an application entry point. "
            f"Add this package to an existing environment with `pipx inject <environment> {library_name}`. "
            f"For a new application environment, place `--preinstall {library_name}` before the application spec."
        )
        if not package_metadata.apps_of_dependencies:
            if venv.safe_to_remove():
                venv.remove_venv()
            msg = f"""
                No apps associated with package {display_name} or its
                dependencies. {library_guidance}
                """
            raise PipxError(msg)
        if package_metadata.apps_of_dependencies and not package_metadata.included_dependency_apps:
            if venv.safe_to_remove():
                venv.remove_venv()
            dependency_apps: Final[str] = "\n".join(
                f"{dependency}: {', '.join(app.name for app in apps)}"
                for dependency, apps in package_metadata.app_paths_of_dependencies.items()
            )
            msg = f"""
                No apps associated with package {display_name}. Use
                '--include-resources-from PACKAGE' to select one of the dependencies
                listed below, or '--include-deps' to include all of them.
                {dependency_apps}
                {library_guidance}
                """
            raise PipxError(msg)

    if venv.pipx_metadata.exposure_enabled:
        expose_package_resources(package_metadata, local_bin_dir, local_man_dir, force=force)
        _remove_stale_venv_resources(previous_resource_paths, venv, local_bin_dir, local_man_dir)

    package_summary, _ = get_venv_summary(venv_dir, package_name=package_name, new_install=True)
    pipx_logger: Final[logging.Logger] = logging.getLogger("pipx")
    if pipx_logger.handlers and pipx_logger.handlers[0].level > logging.WARNING:
        return ()
    messages: Final[list[OutputMessage]] = [OutputMessage(package_summary)]
    if path_warning := warn_if_not_on_path(local_bin_dir):
        messages.append(path_warning)
    messages.append(OutputMessage(f"done! {stars}", stream=OutputStream.STDERR))
    return tuple(messages)


def _remove_stale_venv_resources(
    previous_resource_paths: set[Path],
    venv: Venv,
    local_bin_dir: Path,
    local_man_dir: Path,
) -> None:
    current_resource_paths: Final[set[Path]] = get_expected_venv_resource_paths(venv, local_bin_dir, local_man_dir)
    # only remove a dropped destination pipx still owns, so a replacement the user or another package put there stays
    owned: Final[set[Path]] = _venv_owned_resource_paths(venv, local_bin_dir, local_man_dir)
    for path in sorted((previous_resource_paths - current_resource_paths) & owned):
        safe_unlink(path)


def _venv_owned_resource_paths(venv: Venv, local_bin_dir: Path, local_man_dir: Path) -> set[Path]:
    app_paths: Final[dict[str, list[Path]]] = group_resource_paths(
        (add_suffix(path.name, package.suffix), path)
        for package in venv.package_metadata.values()
        for path in package.app_paths_to_expose
    )
    owned: set[Path] = get_exposed_paths_for_package(venv.bin_path, local_bin_dir, app_paths)
    man_paths: Final[list[Path]] = [
        path for package in venv.package_metadata.values() for path in package.man_paths_to_expose
    ]
    for man_section in MAN_SECTIONS:
        owned |= get_exposed_man_paths_for_package(venv.man_path / man_section, local_man_dir / man_section, man_paths)
    completion_paths: Final[dict[str, list[Path]]] = group_resource_paths(
        (path.name, path) for package in venv.package_metadata.values() for path in package.completion_paths_to_expose
    )
    for completion_section in COMPLETION_SECTIONS:
        owned |= get_exposed_paths_for_package(
            venv.man_path.parent / completion_section,
            paths.ctx.completion_dir / completion_section,
            completion_paths,
        )
    return owned


def get_expected_venv_resource_paths(venv: Venv, local_bin_dir: Path, local_man_dir: Path) -> set[Path]:
    if not venv.pipx_metadata.exposure_enabled:
        return set()
    return (
        {
            local_bin_dir / add_suffix(path.name, package.suffix)
            for package in venv.package_metadata.values()
            for path in package.app_paths_to_expose
        }
        | {
            local_man_dir / path.parent.name / path.name
            for package in venv.package_metadata.values()
            for path in package.man_paths_to_expose
        }
        | {
            paths.ctx.completion_dir / path.parent.parent.name / path.parent.name / path.name
            for package in venv.package_metadata.values()
            for path in package.completion_paths_to_expose
        }
    )


def validate_expected_apps(venv: Venv, package_name: str, expected_apps: Sequence[str]) -> None:
    if not expected_apps:
        return

    package: Final[PackageInfo] = venv.package_metadata[package_name]
    available_apps: Final[list[str]] = sorted({
        app[:-4] if WINDOWS and app.lower().endswith(".exe") else app for app in package.apps_to_expose
    })
    missing_apps: Final[list[str]] = sorted(set(expected_apps) - set(available_apps))
    if missing_apps:
        msg = (
            f"Package {package_name} does not provide expected {'app' if len(missing_apps) == 1 else 'apps'} "
            f"{', '.join(missing_apps)}. "
            f"Available apps: {', '.join(available_apps) or 'none'}."
        )
        raise PipxError(msg)


def warn_if_not_on_path(local_bin_dir: Path) -> OutputMessage | None:
    if not userpath.in_current_path(str(local_bin_dir)):
        return OutputMessage(
            pipx_wrap(
                f"""
                {hazard}  Note: '{local_bin_dir}' is not on your PATH
                environment variable. These apps will not be globally
                accessible until your PATH is updated. Run `pipx ensurepath` to
                automatically add it, or manually modify your PATH in your
                shell's config file (e.g. ~/.bashrc).
                """,
                subsequent_indent=" " * 4,
            ),
            stream=OutputStream.LOG,
        )
    return None


_SUFFIX_ALLOWED: Final[Pattern[str]] = re.compile(r"[A-Za-z0-9._@+-]*")


def validate_suffix(suffix: str) -> str:
    # a suffix is spliced straight into an exposed file name, so anything but a portable character set could steer the
    # destination out of PIPX_BIN_DIR or PIPX_MAN_DIR
    if _SUFFIX_ALLOWED.fullmatch(suffix) is None:
        msg = (
            f"Invalid suffix {suffix!r}. Use only letters, digits, and the characters . _ - + @ so exposed file "
            f"names stay inside pipx's directories."
        )
        raise PipxError(msg)
    return suffix


def add_suffix(name: str, suffix: str) -> str:
    """Add suffix to app."""

    app = Path(name)
    return f"{app.stem}{suffix}{app.suffix}"


def locked_package_message(package_name: str) -> str:
    return f"Not upgrading locked package {package_name}. Update its lock file and run `pipx reinstall {package_name}`."


__all__ = [
    "VenvProblems",
    "add_suffix",
    "can_symlink",
    "expose_package_resources",
    "expose_resources_globally",
    "get_expected_venv_resource_paths",
    "get_exposed_man_paths_for_package",
    "get_exposed_paths_for_package",
    "get_venv_summary",
    "group_resource_paths",
    "locked_package_message",
    "package_name_from_spec",
    "run_post_install_actions",
    "validate_expected_apps",
    "validate_suffix",
    "venv_health_check",
]
