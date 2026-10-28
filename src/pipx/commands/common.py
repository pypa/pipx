from __future__ import annotations

__lazy_modules__ = [
    "collections",
    "filecmp",
    "packaging.utils",
    "pathlib",
    "pipx",
    "pipx.backends",
    "pipx.fanout",
    "pipx.package_specifier",
    "pipx.pipx_metadata_file",
    "pipx.result",
    "pipx.util",
    "pipx.venv",
    "shlex",
    "shutil",
    "tempfile",
    "userpath",
]

import filecmp
import logging
import os
import re
import shlex
import shutil
import tempfile
import time
from collections import Counter
from contextlib import AbstractContextManager, contextmanager, suppress
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from shutil import which
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Final

import userpath
from packaging.utils import canonicalize_name

from pipx import paths
from pipx.backends import PIP, env_default_backend, resolve_backend_name
from pipx.colors import bold, red
from pipx.constants import COMPLETION_SECTIONS, MACOS, MAN_SECTIONS, WINDOWS
from pipx.emojis import hazard, stars
from pipx.fanout import in_turn
from pipx.package_specifier import local_project_name, parse_specifier_for_install, valid_pypi_name
from pipx.pipx_metadata_file import PipxMetadata
from pipx.result import OutputMessage, OutputStream
from pipx.util import PipxError, is_file_name, mkdir, pipx_wrap, safe_unlink
from pipx.venv import Venv, VenvContainer

if TYPE_CHECKING:
    from collections.abc import Collection, Generator, Iterable, Mapping, Sequence

    from pipx.pipx_metadata_file import PackageInfo

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
_IGNORE_ENVIRONMENT_FLAG: Final[bytes] = b" -E"
# macOS refuses a shebang line longer than 512 bytes (newline included) and Linux before 5.1 truncates it at 127, which
# can cut ` -E` to ` -` and make python run stdin; distlib caps the shebangs it writes at the same bounds
_MAX_SHEBANG_LENGTH: Final[int] = 512 if MACOS else 127


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


_SHARED_RESOURCES: Final[ContextVar[frozenset[Path]]] = ContextVar("shared_resources", default=frozenset())


@contextmanager
def expose_shared_resources_in_order(
    venvs_metadata: Iterable[PipxMetadata], local_bin_dir: Path, local_man_dir: Path
) -> Generator[None]:
    # a path several environments of a fan-out expose must end up where a one-at-a-time run leaves it, so they expose
    # it in task order; only shared paths wait, as a task waiting for its turn holds one of the fan-out's workers
    counts: Final[Counter[Path]] = Counter(
        path for metadata in venvs_metadata for path in _shareable_paths(metadata, local_bin_dir, local_man_dir)
    )
    token = _SHARED_RESOURCES.set(frozenset(path for path, count in counts.items() if count > 1))
    try:
        yield
    finally:
        _SHARED_RESOURCES.reset(token)


def _shareable_paths(metadata: PipxMetadata, local_bin_dir: Path, local_man_dir: Path) -> set[Path]:
    try:
        return _expected_resource_paths(
            metadata, (metadata.main_package, *metadata.injected_packages.values()), local_bin_dir, local_man_dir
        )
    except (AttributeError, TypeError):
        # corrupt metadata, such as a null path list, is for the task of its own environment to report
        return set()


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
        # names come from package metadata and pipx_metadata.json; ".." or a path would escape the exposure directory
        if not is_file_name(name := add_suffix(path.name, suffix)):
            msg = f"Refusing to expose {path} as {name!r}, which is not a file name."
            raise PipxError(msg)
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
        with _in_turn_if_shared(dest_dir / add_suffix(path.name, suffix)):
            if (
                collision := _symlink_package_resource(
                    dest_dir,
                    path,
                    force=force,
                    suffix=suffix,
                    executable=(resource_type == "app"),
                )
                if can_symlink(dest_dir)
                else _copy_package_resource(dest_dir, path, force=force, suffix=suffix)
            ) is None:
                _remove_resource_named_before_last_dot(dest_dir, path, suffix)
            else:
                collisions.append(collision)
    return collisions


def _in_turn_if_shared(path: Path) -> AbstractContextManager[None]:
    return in_turn(lambda: path not in _SHARED_RESOURCES.get())


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
    if interpreter.endswith(_IGNORE_ENVIRONMENT_FLAG):
        return
    if b"python" not in interpreter.lower() or b" " in interpreter or b"\t" in interpreter:
        return
    if len(first_line) + len(separator) + len(_IGNORE_ENVIRONMENT_FLAG) > _MAX_SHEBANG_LENGTH:
        return

    path.write_bytes(first_line + _IGNORE_ENVIRONMENT_FLAG + separator + rest)


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

    if force and (symlink_path.is_symlink() or not symlink_path.is_dir()):
        _LOGGER.info("Force is true. Removing %s.", symlink_path)
        with suppress(FileNotFoundError, RuntimeError):
            symlink_path.unlink()

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


def _remove_resource_named_before_last_dot(dest_dir: Path, path: Path, suffix: str) -> None:
    new_name: Final[str] = add_suffix(path.name, suffix)
    for legacy in (dest_dir / name for name in exposed_app_names(path.name, suffix) - {new_name}):
        if legacy.is_symlink():
            owned = legacy.resolve() == path.resolve()
        else:
            # a launcher rebuilt since then no longer matches byte for byte, but its shebang still names this venv
            owned = legacy.is_file() and (
                filecmp.cmp(legacy, path, shallow=False) or _directory_id(path.parent) in _launcher_owner_ids(legacy)
            )
        if owned and drop_copies_claimed_elsewhere({legacy}, path.parent):
            legacy.unlink()
            _LOGGER.warning(
                "%s  Renamed %s to %s, as pipx now puts --suffix at the end of app names", hazard, legacy.name, new_name
            )


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
    app_paths: Final[dict[str, list[Path]]] = group_app_paths(resource_packages)
    exposed_app_paths = get_exposed_paths_for_package(venv.bin_path, paths.ctx.bin_dir, app_paths)
    exposed_binary_names = sorted(path.name for path in exposed_app_paths)
    unavailable_binary_names = sorted({
        add_suffix(name, package_metadata.suffix)
        for name in package_metadata.apps
        if not exposed_app_names(name, package_metadata.suffix) & set(exposed_binary_names)
    })
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


_RESOURCE_DIR_SCANS: Final[ContextVar[dict[Path, _ResourceDirScan] | None]] = ContextVar(
    "resource_dir_scans", default=None
)
_VENV_CLAIMS: Final[ContextVar[dict[Path, set[Path]] | None]] = ContextVar("venv_claims", default=None)


@contextmanager
def reuse_resource_dir_scans() -> Generator[None]:
    # list and uninstall-all ask every venv which exposed resources it owns, so scanning each shared directory once per
    # command instead of once per venv keeps them linear in the number of venvs
    token = _RESOURCE_DIR_SCANS.set({})
    claims_token = _VENV_CLAIMS.set({})
    try:
        yield
    finally:
        _VENV_CLAIMS.reset(claims_token)
        _RESOURCE_DIR_SCANS.reset(token)


def get_exposed_paths_for_package(
    venv_resource_path: Path,
    local_resource_dir: Path,
    package_resource_paths: Mapping[str, Sequence[Path]] | None = None,
) -> set[Path]:
    if not local_resource_dir.exists():
        return set()

    scan: Final[_ResourceDirScan] = _scan_resource_dir(local_resource_dir)
    try:
        exposed = set(scan.by_owner.get(_directory_id(venv_resource_path), ()))
    except OSError:
        exposed = set()
    if can_symlink(local_resource_dir):
        return exposed
    # Man pages and completions carry no launcher shebang, so a copy can only match the venv's own file of the same
    # name or a recorded source; looking up those names avoids comparing every copy with every venv.
    try:
        venv_names = [path.name for path in venv_resource_path.iterdir()]
    except OSError:
        venv_names = []
    return exposed | {
        resource_path
        for name in {os.path.normcase(name) for name in (*venv_names, *(package_resource_paths or {}))}
        for resource_path in scan.by_name.get(name, ())
        if _copy_matches_source(resource_path, venv_resource_path, package_resource_paths)
    }


def drop_copies_claimed_elsewhere(resource_paths: set[Path], venv_bin_path: Path) -> set[Path]:
    # a static script copies byte for byte, so the copy another venv exposes under a name this venv also answers to
    # (tool's run.cmd for tool@2) matches by content; unless its shebang names this venv, it belongs to the other one
    own_id: Final[tuple[int, int] | None] = _directory_id_or_none(venv_bin_path)
    copies: Final[set[Path]] = {
        path for path in resource_paths if not path.is_symlink() and own_id not in _launcher_owner_ids(path)
    }
    return resource_paths - (copies & _claimed_by_other_venvs(venv_bin_path)) if copies else resource_paths


def _directory_id_or_none(path: Path) -> tuple[int, int] | None:
    try:
        return _directory_id(path)
    except OSError:
        return None


def _claimed_by_other_venvs(venv_bin_path: Path) -> set[Path]:
    # a venv removed since the claims were read, as uninstall-all does one by one, no longer holds its paths
    return {
        path
        for venv_dir, claimed in _venv_claims_by_dir().items()
        if not venv_bin_path.is_relative_to(venv_dir) and venv_dir.is_dir()
        for path in claimed
    }


def _venv_claims_by_dir() -> dict[Path, set[Path]]:
    if (cache := _VENV_CLAIMS.get()) is None:
        return _read_venv_claims()
    if not cache:
        cache.update(_read_venv_claims())
    return cache


def _read_venv_claims() -> dict[Path, set[Path]]:
    return {venv_dir: _venv_claims(venv_dir) for venv_dir in VenvContainer(paths.ctx.venvs).iter_venv_dirs()}


def _venv_claims(venv_dir: Path) -> set[Path]:
    metadata: Final[PipxMetadata] = PipxMetadata(venv_dir)
    if not metadata.exposure_enabled or metadata.main_package.package is None:
        return set()
    packages: Final[list[PackageInfo]] = [metadata.main_package, *metadata.injected_packages.values()]
    return _expected_resource_paths(metadata, packages, paths.ctx.bin_dir, paths.ctx.man_dir) | {
        paths.ctx.bin_dir / name
        for package in packages
        for path in package.app_paths_to_expose
        for name in exposed_app_names(path.name, package.suffix)
    }


def _scan_resource_dir(local_resource_dir: Path) -> _ResourceDirScan:
    if (scans := _RESOURCE_DIR_SCANS.get()) is None:
        return _build_resource_dir_scan(local_resource_dir)
    if local_resource_dir not in scans:
        scans[local_resource_dir] = _build_resource_dir_scan(local_resource_dir)
    return scans[local_resource_dir]


def _build_resource_dir_scan(local_resource_dir: Path) -> _ResourceDirScan:
    owner_ids: Final = _symlink_owner_ids if can_symlink(local_resource_dir) else _launcher_owner_ids
    by_owner: Final[dict[tuple[int, int], set[Path]]] = {}
    by_name: Final[dict[str, list[Path]]] = {}
    for resource_path in local_resource_dir.iterdir():
        by_name.setdefault(os.path.normcase(resource_path.name), []).append(resource_path)
        for owner_id in owner_ids(resource_path):
            by_owner.setdefault(owner_id, set()).add(resource_path)
    return _ResourceDirScan(by_owner, by_name)


@dataclass(frozen=True)
class _ResourceDirScan:
    by_owner: dict[tuple[int, int], set[Path]]
    by_name: dict[str, list[Path]]


def _symlink_owner_ids(resource_path: Path) -> list[tuple[int, int]]:
    # Some apps expose symlinks whose names differ from their targets, so resolved paths cannot identify them.
    try:
        return [_directory_id(resource_path.resolve().parent)] if resource_path.is_symlink() else []
    except (FileNotFoundError, RuntimeError):
        return []


def _launcher_owner_ids(resource_path: Path) -> list[tuple[int, int]]:
    # A copied launcher keeps a shebang to the venv interpreter it was built for, so a stale copy is still
    # recognised even after a force reinstall regenerates its source (the rewritten launcher no longer
    # byte-matches, and Windows .exe stubs also embed install-time timestamps), while another venv's colliding
    # copy is not.
    try:
        data: Final[bytes] = resource_path.read_bytes()
    except OSError:
        return []
    owner_ids: Final[list[tuple[int, int]]] = []
    # A console-script launcher embeds a "#!<interpreter>" line: the first line on POSIX, and on Windows a line
    # tucked between the .exe launcher stub and the appended zip. Both point the copy at its owning venv.
    start = 0
    while (marker := data.find(b"#!", start)) != -1:
        start = marker + 2
        end = data.find(b"\n", marker)
        line = (data[start:] if end == -1 else data[start:end]).strip()
        if line.startswith(b'"'):
            interpreter = line[1:close] if (close := line.find(b'"', 1)) != -1 else b""
        else:
            interpreter = parts[0] if (parts := line.split()) else b""
        try:
            if interpreter:
                owner_ids.append(_directory_id(Path(os.fsdecode(interpreter)).parent))
        except (OSError, ValueError):
            # The scan reads every file in the bin directory, so a stray "#!" in a foreign binary leads here with
            # arbitrary bytes rather than a path: os.fsdecode rejects undecodable ones under the surrogatepass
            # codec Windows uses, and stat rejects an embedded NUL. Neither makes the copy ours.
            continue
    return owner_ids


def _directory_id(path: Path) -> tuple[int, int]:
    # the identity Path.samefile compares, so a venv reached through a different spelling still matches
    return (stat := path.stat()).st_dev, stat.st_ino


def _copy_matches_source(
    resource_path: Path,
    venv_resource_path: Path,
    package_resource_paths: Mapping[str, Sequence[Path]] | None,
) -> bool:
    # a static resource copies byte-for-byte, while a colliding copy from another package differs
    try:
        same_named: Final[Path] = venv_resource_path / resource_path.name
        if same_named.is_file() and filecmp.cmp(resource_path, same_named, shallow=False):
            return True
        sources = (package_resource_paths or {}).get(resource_path.name, ())
        return any(source.is_file() and filecmp.cmp(resource_path, source, shallow=False) for source in sources)
    except FileNotFoundError:
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


def group_app_paths(packages: Iterable[PackageInfo]) -> dict[str, list[Path]]:
    return group_resource_paths(
        (name, path)
        for package in packages
        for path in package.app_paths_to_expose
        for name in exposed_app_names(path.name, package.suffix)
    )


def group_resource_paths(resource_paths: Iterable[tuple[str, Path]]) -> dict[str, list[Path]]:
    grouped: dict[str, list[Path]] = {}
    for name, path in resource_paths:
        grouped.setdefault(name, []).append(path)
    return grouped


def _get_list_output(  # ruff:ignore[too-many-arguments]  # flat rendering inputs; a wrapper struct would only add indirection
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


def package_name_from_spec(  # ruff:ignore[too-many-arguments]  # resolver inputs are independent scalars, not a cohesive struct
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

    if (project_name := local_project_name(package_spec)) is not None:
        backend_name, _ = resolve_backend_name(
            cli_value=backend, env_value=env_default_backend() if env_backend is None else env_backend
        )
        # match what the installer would report: pip lists the declared name, uv the normalized one
        package_name = project_name if backend_name == PIP else canonicalize_name(project_name)
        _LOGGER.info("Determined package name: %s", package_name)
        _LOGGER.info("Package name determined in %.1fs", time.time() - start_time)
        return package_name

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


def run_post_install_actions(  # ruff:ignore[too-many-arguments]  # post-install needs venv, both resource dirs, and the venv dir
    venv: Venv,
    package_name: str,
    local_bin_dir: Path,
    local_man_dir: Path,
    venv_dir: Path,
    *,
    force: bool,
    previous_resource_paths: set[Path],
) -> tuple[OutputMessage, ...]:
    # ``package_name`` is the metadata key, so it must stay the bare package name:
    # the record's own ``suffix`` field already renders the environment suffix in
    # the summary below, and looking the key up by a suffixed name would miss.
    package_metadata = venv.package_metadata[package_name]

    display_name = f"{package_name}{package_metadata.suffix}"

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
        remove_stale_venv_resources(previous_resource_paths, venv, local_bin_dir, local_man_dir)

    package_summary, _ = get_venv_summary(venv_dir, package_name=package_name, new_install=True)
    pipx_logger: Final[logging.Logger] = logging.getLogger("pipx")
    if pipx_logger.handlers and pipx_logger.handlers[0].level > logging.WARNING:
        return ()
    messages: Final[list[OutputMessage]] = [OutputMessage(package_summary)]
    if path_warning := warn_if_not_on_path(local_bin_dir):
        messages.append(path_warning)
    messages.append(OutputMessage(f"done! {stars}", stream=OutputStream.STDERR))
    return tuple(messages)


def remove_stale_venv_resources(
    previous_resource_paths: set[Path],
    venv: Venv,
    local_bin_dir: Path,
    local_man_dir: Path,
) -> None:
    current_resource_paths: Final[set[Path]] = get_expected_venv_resource_paths(venv, local_bin_dir, local_man_dir)
    # only remove a dropped destination pipx still owns, so a replacement the user or another package put there stays
    owned: Final[set[Path]] = _venv_owned_resource_paths(venv, local_bin_dir, local_man_dir)
    for path in sorted(
        drop_copies_claimed_elsewhere((previous_resource_paths - current_resource_paths) & owned, venv.bin_path)
    ):
        safe_unlink(path)


def _venv_owned_resource_paths(venv: Venv, local_bin_dir: Path, local_man_dir: Path) -> set[Path]:
    owned: set[Path] = get_exposed_paths_for_package(
        venv.bin_path, local_bin_dir, group_app_paths(venv.package_metadata.values())
    )
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
    return _expected_resource_paths(venv.pipx_metadata, venv.package_metadata.values(), local_bin_dir, local_man_dir)


def _expected_resource_paths(
    metadata: PipxMetadata, packages: Collection[PackageInfo], local_bin_dir: Path, local_man_dir: Path
) -> set[Path]:
    if not metadata.exposure_enabled:
        return set()
    return (
        {
            local_bin_dir / add_suffix(path.name, package.suffix)
            for package in packages
            for path in package.app_paths_to_expose
        }
        | {local_man_dir / path.parent.name / path.name for package in packages for path in package.man_paths_to_expose}
        | {
            paths.ctx.completion_dir / path.parent.parent.name / path.parent.name / path.name
            for package in packages
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
    # Windows opens a file by its extension, so hello.py becomes hello@1.py there; the 14 of pip3.14 is a version, not
    # an extension, and POSIX ignores extensions, so elsewhere the suffix goes last
    app: Final[Path] = Path(name)
    if WINDOWS and app.suffix and not app.suffix[1:].isdigit():
        return f"{app.stem}{suffix}{app.suffix}"
    return f"{name}{suffix}"


def exposed_app_names(name: str, suffix: str) -> set[str]:
    # pipx 1.17.14 and earlier put the suffix before the last dot (pip3@1.12 for pip3.12), and an app exposed back then
    # keeps that name until pipx exposes it again
    app: Final[Path] = Path(name)
    return {add_suffix(name, suffix), f"{app.stem}{suffix}{app.suffix}"}


def locked_package_message(package_name: str) -> str:
    return f"Not upgrading locked package {package_name}. Update its lock file and run `pipx reinstall {package_name}`."


__all__ = [
    "VenvProblems",
    "add_suffix",
    "can_symlink",
    "drop_copies_claimed_elsewhere",
    "expose_package_resources",
    "expose_resources_globally",
    "expose_shared_resources_in_order",
    "exposed_app_names",
    "get_expected_venv_resource_paths",
    "get_exposed_man_paths_for_package",
    "get_exposed_paths_for_package",
    "get_venv_summary",
    "group_app_paths",
    "group_resource_paths",
    "locked_package_message",
    "package_name_from_spec",
    "remove_stale_venv_resources",
    "reuse_resource_dir_scans",
    "run_post_install_actions",
    "validate_expected_apps",
    "validate_suffix",
    "venv_health_check",
]
