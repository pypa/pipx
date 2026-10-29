from __future__ import annotations

__lazy_modules__ = [
    "collections",
    "filecmp",
    "importlib.machinery",
    "packaging.utils",
    "pathlib",
    "pipx",
    "pipx.backends._base",
    "pipx.backends.registry",
    "pipx.fanout",
    "pipx.package_specifier",
    "pipx.pipx_metadata_file",
    "pipx.result",
    "pipx.trash",
    "pipx.util",
    "pipx.venv",
    "pipx.wrap",
    "re",
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
import sys
import tempfile
import time
from collections import Counter
from contextlib import AbstractContextManager, contextmanager, suppress
from contextvars import ContextVar
from dataclasses import dataclass, fields
from importlib.machinery import all_suffixes
from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Final, Literal

import userpath
from packaging.utils import canonicalize_name

from pipx import paths
from pipx.backends._base import PIP
from pipx.backends.registry import env_default_backend, resolve_backend_name
from pipx.colors import BOLD, RED
from pipx.constants import COMPLETION_SECTIONS, MACOS, MAN_SECTIONS, WINDOWS
from pipx.emojis import HAZARD, STARS
from pipx.fanout import in_turn
from pipx.package_specifier import local_project_name, parse_specifier_for_install, valid_pypi_name
from pipx.pipx_metadata_file import PIPX_INFO_FILENAME, PackageInfo, PipxMetadata
from pipx.result import OutputMessage, OutputStream
from pipx.trash import safe_unlink
from pipx.util import PipxError, is_file_name, mkdir
from pipx.venv import Venv, VenvContainer
from pipx.wrap import pipx_wrap

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Generator, Iterable, Mapping, Sequence

    from pipx.options import BackendOptions
    from pipx.venv_inspect import VenvMetadata

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
_SHARED_RESOURCES: Final[ContextVar[frozenset[Path]]] = ContextVar("shared_resources", default=frozenset())
# shared links a fan-out task took over because they dangled, with the target they had and the one written
_DANGLING_TAKEN: Final[ContextVar[dict[Path, tuple[Path, Path]]]] = ContextVar("dangling_taken")
# None is a user's --force, which replaces whatever holds a name
_REPLACEABLE_RESOURCES: Final[ContextVar[frozenset[Path] | None]] = ContextVar("replaceable_resources", default=None)
_RESOURCE_DIR_SCANS: Final[ContextVar[dict[Path, _ResourceDirScan] | None]] = ContextVar(
    "resource_dir_scans", default=None
)
_VENV_CLAIMS: Final[ContextVar[dict[Path, set[Path]] | None]] = ContextVar("venv_claims", default=None)
_CAN_SYMLINK_CACHE: Final[dict[Path, bool]] = {}


@contextmanager
def force_replaces_only(resource_paths: Iterable[Path]) -> Generator[None]:
    # a rebuild forces only to refresh its own exposed files, not to take names install left with their owner
    token: Final = _REPLACEABLE_RESOURCES.set(frozenset(resource_paths))
    try:
        yield
    finally:
        _REPLACEABLE_RESOURCES.reset(token)


@contextmanager
def expose_shared_resources_in_order(
    venvs_metadata: Iterable[PipxMetadata], local_bin_dir: Path, local_man_dir: Path
) -> Generator[None]:
    # a path several environments of a fan-out expose must end up where a one-at-a-time run leaves it, so they expose
    # it in task order; only shared paths wait, as a task waiting for its turn holds one of the fan-out's workers
    counts: Final[Counter[Path]] = Counter(
        path for metadata in venvs_metadata for path in _shareable_paths(metadata, local_bin_dir, local_man_dir)
    )
    token: Final = _SHARED_RESOURCES.set(frozenset(path for path, count in counts.items() if count > 1))
    taken_token: Final = _DANGLING_TAKEN.set({})
    try:
        yield
    finally:
        _DANGLING_TAKEN.reset(taken_token)
        _SHARED_RESOURCES.reset(token)


def _shareable_paths(metadata: PipxMetadata, local_bin_dir: Path, local_man_dir: Path) -> set[Path]:
    try:
        return _expected_resource_paths(
            metadata, (metadata.main_package, *metadata.injected_packages.values()), local_bin_dir, local_man_dir
        )
    except (AttributeError, TypeError):
        # corrupt metadata, such as a null path list, is for the task of its own environment to report
        return set()


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
            paths.CTX.completion_dir / path.parent.parent.name / path.parent.name / path.name
            for package in packages
            for path in package.completion_paths_to_expose
        }
    )


def add_suffix(name: str, suffix: str) -> str:
    # Windows opens a file by its extension, so hello.py becomes hello@1.py there; the 14 of pip3.14 is a version, not
    # an extension, and POSIX ignores extensions, so elsewhere the suffix goes last
    app: Final[Path] = Path(name)
    if WINDOWS and app.suffix and not app.suffix[1:].isdigit():
        return f"{app.stem}{suffix}{app.suffix}"
    return f"{name}{suffix}"


@contextmanager
def reuse_resource_dir_scans() -> Generator[None]:
    # list and uninstall-all ask every venv which exposed resources it owns, so scanning each shared directory once per
    # command instead of once per venv keeps them linear in the number of venvs
    token: Final = _RESOURCE_DIR_SCANS.set({})
    claims_token: Final = _VENV_CLAIMS.set({})
    try:
        yield
    finally:
        _VENV_CLAIMS.reset(claims_token)
        _RESOURCE_DIR_SCANS.reset(token)


def drop_links_taken_over(resource_paths: set[Path], *venv_dirs: Path) -> set[Path]:
    # a link dangles while its venv is rebuilt or its package uninstalled, and the next package claiming a dangling name
    # takes it, so a path gathered before then is still the venv's only if it links into the venv
    venv_roots: Final[list[Path]] = [venv_dir.resolve() for venv_dir in venv_dirs]
    return {
        path
        for path in resource_paths
        if (
            any(_link_target(path).is_relative_to(venv_root) for venv_root in venv_roots)
            if path.is_symlink()
            else not can_symlink(path.parent)
        )
    }


def _link_target(link: Path) -> Path:
    # with UV_LINK_MODE=symlink the venv's own file links on into uv's cache, so only the first hop names the venv
    target: Final[Path] = link.parent / _without_extended_prefix(str(link.readlink()))
    return target.parent.resolve() / target.name


def _without_extended_prefix(target: str) -> str:
    # Windows reads a link target back as \\?\C:\... or \\?\UNC\server\share\..., a spelling resolve() keeps while the
    # venv paths compared against never use it
    if not WINDOWS:
        return target
    if target.startswith(unc := "\\\\?\\UNC\\"):
        return target.replace(unc, "\\\\", 1)
    return target.removeprefix("\\\\?\\")


def can_symlink(local_resource_dir: Path) -> bool:
    if not WINDOWS:
        # even on Unix this depends on the filesystem
        return True

    if local_resource_dir not in _CAN_SYMLINK_CACHE:
        with TemporaryDirectory(dir=local_resource_dir) as directory:
            (target := Path(directory) / "a").touch()
            try:
                (Path(directory) / "b").symlink_to(target)
                _CAN_SYMLINK_CACHE[local_resource_dir] = True
            except (OSError, NotImplementedError):
                _CAN_SYMLINK_CACHE[local_resource_dir] = False

    return _CAN_SYMLINK_CACHE[local_resource_dir]


def give_back_shared_links(resource_paths: set[Path], venv_dir: Path) -> None:
    # a link dangles while its venv sits in the trash for a rebuild, and an earlier fan-out task exposing the same name
    # meanwhile takes it; a failed rebuild gives the name back, as a one-at-a-time run would have left it
    for path in resource_paths & _SHARED_RESOURCES.get():
        with _in_turn_if_shared(path):
            if (taken := _DANGLING_TAKEN.get().get(path)) is None:
                continue
            dangling, written = taken
            # a link pointing elsewhere than the takeover left it was replaced since, such as by another run's --force
            if (
                path.is_symlink()
                and path.resolve() == written.resolve()
                and (restored := (path.parent / dangling).resolve()).is_relative_to(venv_dir.resolve())
                and restored.exists()
            ):
                path.unlink()
                path.symlink_to(dangling)


def package_name_from_spec(  # ruff:ignore[too-many-arguments]  # resolver inputs are independent scalars, not a cohesive struct
    package_spec: str,
    python: str,
    *,
    pip_args: list[str],
    verbose: bool,
    backend: BackendOptions,
    cooldown_days: int | None = None,
) -> str:
    start_time: Final[float] = time.time()

    if (pypi_name := valid_pypi_name(package_spec)) is not None:
        # pipx keeps the PyPI name even when the installed distribution calls itself something else
        _LOGGER.info("Determined package name: %s", pypi_name)
        _LOGGER.info("Package name determined in %.1fs", time.time() - start_time)
        return pypi_name

    package_spec, pip_args = parse_specifier_for_install(package_spec, pip_args)

    if (project_name := local_project_name(package_spec)) is not None:
        backend_name, _ = resolve_backend_name(
            cli_value=backend.cli, env_value=env_default_backend() if backend.env is None else backend.env
        )
        # match what the installer would report: pip lists the declared name, uv the normalized one
        package_name = project_name if backend_name == PIP else canonicalize_name(project_name)
        _LOGGER.info("Determined package name: %s", package_name)
        _LOGGER.info("Package name determined in %.1fs", time.time() - start_time)
        return package_name

    with tempfile.TemporaryDirectory() as temp_venv_dir:
        venv = Venv(Path(temp_venv_dir), python=python, verbose=verbose, backend=backend)
        # under pip this can be the call that builds the shared libraries, so their pip must come from the user's index
        venv.create_venv(venv_args=[], pip_args=pip_args)
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
    # package_name is the metadata key, so it stays the bare name; the record's suffix field renders the suffix in the
    # summary below
    package_metadata: Final[PackageInfo] = venv.package_metadata[package_name]
    display_name: Final[str] = f"{package_name}{package_metadata.suffix}"

    if not package_metadata.apps:
        library_name: Final[str] = package_metadata.package or package_name
        library_guidance: Final[str] = (
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
        if not package_metadata.included_dependency_apps:
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
    messages: Final[list[OutputMessage]] = [OutputMessage(text=package_summary)]
    if path_warning := _warn_if_not_on_path(local_bin_dir):
        messages.append(path_warning)
    messages.append(OutputMessage(text=f"done! {STARS}", stream=OutputStream.STDERR))
    return tuple(messages)


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
            expose_resources_globally("completion", paths.CTX.completion_dir, completion_paths, force=force)
        )
    return collisions


def expose_resources_globally(
    resource_type: str,
    local_resource_dir: Path,
    resource_paths: list[Path],
    *,
    force: bool,
    suffix: str = "",
) -> list[Path]:
    collisions: Final[list[Path]] = []
    for path in resource_paths:
        # names come from package metadata and pipx_metadata.json; ".." or a path would escape the exposure directory
        if not is_file_name(name := add_suffix(path.name, suffix)):
            msg = f"Refusing to expose {path} as {name!r}, which is not a file name."
            raise PipxError(msg)
        if resource_type == "app":
            if module := _shadowed_module(name, path):
                _LOGGER.warning(
                    "%s  Not exposing %s: a Python script started from %s, such as pip's pipx launcher, would import "
                    "it in place of the %s module.",
                    HAZARD,
                    name,
                    local_resource_dir,
                    module,
                )
                continue
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
        with _in_turn_if_shared(dest_dir / name):
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


def _shadowed_module(name: str, path: Path) -> str | None:
    # a script started from the bin dir, such as pip's pipx launcher, searches that dir first, and the launcher imports
    # re (and through it enum, functools and more) and then pipx itself before pipx can drop the entry from sys.path
    shadowed: Final[frozenset[str]] = frozenset({*sys.stdlib_module_names, "pipx"})
    if path.is_dir():
        return name if name in shadowed else None
    return next(
        (module for suffix in all_suffixes() if (module := name.removesuffix(suffix)) != name and module in shadowed),
        None,
    )


def _add_ignore_environment_to_python_shebang(path: Path) -> None:
    if WINDOWS or not path.is_file():
        return

    try:
        first_line, separator, rest = path.read_bytes().partition(b"\n")
    except OSError:
        return
    if not first_line.startswith(b"#!"):
        return

    flag: Final[bytes] = b" -E"
    interpreter: Final[bytes] = first_line[2:]
    if interpreter.endswith(flag):
        return
    if b"python" not in interpreter.lower() or b" " in interpreter or b"\t" in interpreter:
        return
    # macOS refuses a shebang line longer than 512 bytes (newline included) and Linux before 5.1 truncates it at 127,
    # which can cut ` -E` to ` -` and make python run stdin; distlib caps the shebangs it writes at the same bounds
    if len(first_line) + len(separator) + len(flag) > (512 if MACOS else 127):
        return

    # uv hard-links or symlinks installed files to its cache, which other environments share, so write a new inode
    with TemporaryDirectory(dir=path.parent) as directory:
        (rewritten := Path(directory) / path.name).write_bytes(first_line + flag + separator + rest)
        shutil.copymode(path, rewritten)
        rewritten.replace(path)


def _in_turn_if_shared(path: Path) -> AbstractContextManager[None]:
    return in_turn(lambda: path not in _SHARED_RESOURCES.get())


def _symlink_package_resource(
    dest_dir: Path,
    path: Path,
    *,
    force: bool,
    suffix: str,
    executable: bool,
) -> Path | None:
    name_suffixed: Final[str] = add_suffix(path.name, suffix)
    symlink_path: Final[Path] = dest_dir / name_suffixed

    if not symlink_path.parent.is_dir():
        mkdir(symlink_path.parent)

    if force and _force_replaces(symlink_path) and (symlink_path.is_symlink() or not symlink_path.is_dir()):
        _LOGGER.info("Force is true. Removing %s.", symlink_path)
        with suppress(FileNotFoundError, RuntimeError):
            symlink_path.unlink()

    exists: Final[bool] = symlink_path.exists()
    is_symlink: Final[bool] = symlink_path.is_symlink()
    if exists or (is_symlink and _links_into_another_venv(symlink_path, path)):
        if exists and symlink_path.samefile(path):
            _LOGGER.info("Same path %s and %s", symlink_path, path)
            return None
        _LOGGER.warning(
            pipx_wrap(
                f"""
                {HAZARD}  File exists at {symlink_path!s} and points
                to {symlink_path.resolve()}{"" if exists else ", which is missing"}. pipx leaves it in
                place instead of linking it to {path!s}.
                """,
                subsequent_indent=" " * 4,
            )
        )
        return symlink_path
    if is_symlink and not exists:
        _LOGGER.info("Removing existing symlink %s because it points to a missing location", symlink_path)
        if symlink_path in _SHARED_RESOURCES.get():
            _DANGLING_TAKEN.get()[symlink_path] = (symlink_path.readlink(), path)
        symlink_path.unlink()

    existing_executable_on_path: Final[str | None] = which(name_suffixed) if executable else None
    symlink_path.symlink_to(path)

    if existing_executable_on_path:
        _LOGGER.warning(
            pipx_wrap(
                f"""
                {HAZARD}  Note: {name_suffixed} was already on your
                PATH at {existing_executable_on_path}
                """,
                subsequent_indent=" " * 4,
            )
        )
    return None


def _force_replaces(path: Path) -> bool:
    return (replaceable := _REPLACEABLE_RESOURCES.get()) is None or path in replaceable


def _links_into_another_venv(symlink_path: Path, path: Path) -> bool:
    # an installer removes a package's old files before it writes the new ones, and another task of a fan-out or another
    # pipx run can expose meanwhile, so a dangling link into a venv that still exists is that venv's, not a left-over
    venvs: Final[Path] = paths.CTX.venvs.resolve()
    try:
        target: Final[Path] = symlink_path.resolve()
    except RuntimeError:  # a symlink loop, which Python before 3.13 reports this way
        return False
    venv_dir: Final[Path | None] = next((parent for parent in target.parents if parent.parent == venvs), None)
    return (
        venv_dir is not None
        and venv_dir.is_dir()
        and not path.resolve().is_relative_to(venv_dir)
        and _still_exposed_by(venv_dir, target)
    )


def _still_exposed_by(venv_dir: Path, target: Path) -> bool:
    # pipx before 1.18.0 kept the link when a new release dropped the app, so a resource the venv's metadata no longer
    # lists is a left-over, not a file an installer is rewriting
    metadata: Final[PipxMetadata] = PipxMetadata(venv_dir)
    if metadata.read_metadata_version is None:  # unreadable metadata can't prove the link stale
        return True
    return any(
        resource.resolve() == target
        for package in (metadata.main_package, *metadata.injected_packages.values())
        for resource in (
            *package.app_paths_to_expose,
            *package.man_paths_to_expose,
            *package.completion_paths_to_expose,
        )
    )


def _copy_package_resource(dest_dir: Path, path: Path, *, force: bool, suffix: str) -> Path | None:
    src: Final[Path] = path.resolve()
    dest: Final[Path] = dest_dir / add_suffix(src.name, suffix)
    if not dest.parent.is_dir():
        mkdir(dest.parent)
    if dest.exists():
        if filecmp.cmp(dest, src, shallow=False):
            return None
        if not force or not _force_replaces(dest):
            _LOGGER.warning("%s  File exists at %s and does not match %s. Not modifying.", HAZARD, dest, src)
            return dest
        # a rebuilt launcher no longer matches its old copy (Windows .exe stubs embed their build time), but a copy
        # whose shebang names this venv is the one pipx exposed, so refreshing it needs no warning
        if _directory_id_or_none(src.parent) in _launcher_owner_ids(dest):
            _LOGGER.info("Refreshing %s from %s", dest, src)
        else:
            _LOGGER.warning("%s  Overwriting file %s with %s", HAZARD, dest, src)
        safe_unlink(dest)
    if src.exists():
        shutil.copy(src, dest)
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
                "%s  Renamed %s to %s, as pipx now puts --suffix at the end of app names", HAZARD, legacy.name, new_name
            )


def exposed_app_names(name: str, suffix: str) -> set[str]:
    # pipx 1.17.14 and earlier put the suffix before the last dot (pip3@1.12 for pip3.12), and an app exposed back then
    # keeps that name until pipx exposes it again
    app: Final[Path] = Path(name)
    return {add_suffix(name, suffix), f"{app.stem}{suffix}{app.suffix}"}


def _directory_id(path: Path) -> tuple[int, int]:
    # the identity Path.samefile compares, so a venv reached through a different spelling still matches
    return (stat := path.stat()).st_dev, stat.st_ino


def _launcher_owner_ids(resource_path: Path) -> list[tuple[int, int]]:
    # a copied launcher keeps a shebang to the venv interpreter it was built for, so a force reinstall that rewrites its
    # source (and Windows .exe stubs, which embed install-time timestamps) still leaves a stale copy recognisable, while
    # another venv's colliding copy is not
    try:
        data: Final[bytes] = resource_path.read_bytes()
    except OSError:
        return []
    owner_ids: Final[list[tuple[int, int]]] = []
    # the "#!<interpreter>" line is the first line on POSIX, and on Windows sits between the .exe launcher stub and the
    # appended zip
    start = 0
    while (marker := data.find(b"#!", start)) != -1:
        start = marker + 2
        end = len(data) if (newline := data.find(b"\n", start)) == -1 else newline
        next_end = len(data) if (newline := data.find(b"\n", end + 1)) == -1 else newline
        # the scan reads every file in the bin directory, so a stray "#!" in a foreign binary hands over arbitrary
        # bytes: os.fsdecode rejects undecodable ones under the surrogatepass codec Windows uses, shlex unbalanced
        # quotes, and stat an embedded NUL; none makes the copy ours
        with suppress(OSError, ValueError):
            if interpreter := _shebang_interpreter(data[start:end].strip(), data[end + 1 : next_end]):
                owner_ids.append(_directory_id(Path(interpreter).parent))
    return owner_ids


def _shebang_interpreter(line: bytes, next_line: bytes) -> str:
    if line == b"/bin/sh" and next_line.startswith(b"'''exec' "):
        # pip and uv write a /bin/sh trampoline when the interpreter path is too long for a shebang or holds a space,
        # and name the interpreter, shell-quoted, on the exec line that follows
        words: Final[list[str]] = shlex.split(os.fsdecode(next_line))
        return words[1] if len(words) > 1 else ""
    if line.startswith(b'"'):
        return os.fsdecode(line[1:close]) if (close := line.find(b'"', 1)) != -1 else ""
    return os.fsdecode(parts[0]) if (parts := line.split()) else ""


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
    return {venv_dir: _venv_claims(venv_dir) for venv_dir in VenvContainer(paths.CTX.venvs).iter_venv_dirs()}


def _venv_claims(venv_dir: Path) -> set[Path]:
    metadata: Final[PipxMetadata] = PipxMetadata(venv_dir)
    if not metadata.exposure_enabled or metadata.main_package.package is None:
        return set()
    packages: Final[list[PackageInfo]] = [metadata.main_package, *metadata.injected_packages.values()]
    return _expected_resource_paths(metadata, packages, paths.CTX.bin_dir, paths.CTX.man_dir) | {
        paths.CTX.bin_dir / name
        for package in packages
        for path in package.app_paths_to_expose
        for name in exposed_app_names(path.name, package.suffix)
    }


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


def get_expected_venv_resource_paths(venv: Venv, local_bin_dir: Path, local_man_dir: Path) -> set[Path]:
    return _expected_resource_paths(venv.pipx_metadata, venv.package_metadata.values(), local_bin_dir, local_man_dir)


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
            paths.CTX.completion_dir / completion_section,
            completion_paths,
        )
    return owned


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
    return _ResourceDirScan(by_owner=by_owner, by_name=by_name)


def _symlink_owner_ids(resource_path: Path) -> list[tuple[int, int]]:
    # Some apps expose symlinks whose names differ from their targets, so resolved paths cannot identify them.
    try:
        return [_directory_id(_link_target(resource_path).parent)] if resource_path.is_symlink() else []
    except (FileNotFoundError, RuntimeError):
        return []


@dataclass(frozen=True, slots=True, kw_only=True)
class _ResourceDirScan:
    by_owner: dict[tuple[int, int], set[Path]]
    by_name: dict[str, list[Path]]


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
        return any(
            source.is_file() and filecmp.cmp(resource_path, source, shallow=False)
            for source in (package_resource_paths or {}).get(resource_path.name, ())
        )
    except FileNotFoundError:
        return False


def group_app_paths(packages: Iterable[PackageInfo]) -> dict[str, list[Path]]:
    return group_resource_paths(
        (name, path)
        for package in packages
        for path in package.app_paths_to_expose
        for name in exposed_app_names(path.name, package.suffix)
    )


def group_resource_paths(resource_paths: Iterable[tuple[str, Path]]) -> dict[str, list[Path]]:
    grouped: Final[dict[str, list[Path]]] = {}
    for name, path in resource_paths:
        grouped.setdefault(name, []).append(path)
    return grouped


def get_exposed_man_paths_for_package(
    venv_man_path: Path,
    local_man_dir: Path,
    package_man_paths: Sequence[Path],
) -> set[Path]:
    return get_exposed_paths_for_package(
        venv_man_path,
        local_man_dir,
        group_resource_paths((path.name, path) for path in package_man_paths if path.parent.name == venv_man_path.name),
    )


def get_venv_summary(
    venv_dir: Path,
    *,
    package_name: str | None = None,
    new_install: bool = False,
    include_injected: bool = False,
) -> tuple[str, VenvProblems]:
    venv: Final[Venv] = Venv(venv_dir)

    if package_name is None:
        package_name = venv.main_package_name

    venv_problems, warning_message = venv_health_check(venv, package_name)
    if venv_problems.any_():
        return (warning_message, venv_problems)
    return (
        _get_list_output(venv, package_name, new_install=new_install, include_injected=include_injected),
        venv_problems,
    )


def venv_health_check(venv: Venv, package_name: str | None = None) -> tuple[VenvProblems, str]:
    venv_dir: Final[Path] = venv.root
    python_path: Final[Path] = venv.python_path.resolve()

    if package_name is None:
        package_name = venv.main_package_name

    if not python_path.is_file():
        return (
            VenvProblems(invalid_interpreter=True),
            f"   package {RED(BOLD(venv_dir.name))} has invalid interpreter {python_path!s}\r{HAZARD}",
        )
    # the metadata is owner-only as it can hold index credentials, so another user sees a --global environment this way
    metadata_file: Final[Path] = venv_dir / PIPX_INFO_FILENAME
    if not venv.package_metadata and metadata_file.exists() and not os.access(metadata_file, os.R_OK):
        return (
            VenvProblems(unreadable_metadata=True),
            f"   package {RED(BOLD(venv_dir.name))} has pipx metadata this user cannot read.\r{HAZARD}",
        )
    if not venv.package_metadata:
        return (
            VenvProblems(missing_metadata=True),
            f"   package {RED(BOLD(venv_dir.name))} has no internal pipx metadata.\r{HAZARD}",
        )
    if venv_dir.name != canonicalize_name(venv_dir.name):
        return (
            VenvProblems(bad_venv_name=True),
            f"   package {RED(BOLD(venv_dir.name))} needs its internal data updated.\r{HAZARD}",
        )
    if not venv.package_metadata[package_name].package_version:
        return (
            VenvProblems(not_installed=True),
            f"   package {RED(BOLD(package_name))} {RED('is not installed')} in the venv {venv_dir.name}\r{HAZARD}",
        )
    return (VenvProblems(), "")


@dataclass(frozen=True, slots=True, kw_only=True)
class VenvProblems:
    bad_venv_name: bool = False
    invalid_interpreter: bool = False
    missing_metadata: bool = False
    unreadable_metadata: bool = False
    not_installed: bool = False

    def any_(self) -> bool:
        return any(getattr(self, field.name) for field in fields(self))

    def or_(self, venv_problems: VenvProblems) -> VenvProblems:
        return VenvProblems(**{
            field.name: getattr(self, field.name) or getattr(venv_problems, field.name) for field in fields(self)
        })


def _get_list_output(venv: Venv, package_name: str, *, new_install: bool, include_injected: bool) -> str:
    package_metadata: Final[PackageInfo] = venv.package_metadata[package_name]
    python_version: Final[str | None] = venv.pipx_metadata.python_version
    source_interpreter: Final[Path | None] = venv.pipx_metadata.source_interpreter
    standalone: Final[str] = (
        " (standalone)"
        if source_interpreter
        and str(source_interpreter).startswith(str(paths.CTX.standalone_python_cachedir.resolve()))
        else ""
    )
    suffix: Final[str] = (
        f" ({BOLD(shlex.quote(f'{package_name}{package_metadata.suffix}'))})" if package_metadata.suffix else ""
    )
    output: Final[list[str]] = [
        (
            f"  {'installed' if new_install else ''} package {BOLD(shlex.quote(package_name))}"
            f" {BOLD(package_metadata.package_version)}{suffix}, installed using "
            f"{python_version if python_version is not None else ''}{standalone}"
        )
    ]

    if venv.pipx_metadata.exposure_enabled:
        exposed_binary_names, unavailable_binary_names, exposed_man_pages, unavailable_man_pages = (
            _get_exposed_resource_names(venv, package_metadata, new_install=new_install)
        )
        if new_install and (exposed_binary_names or unavailable_binary_names):
            output.append("  These apps are now available")
        output.extend(f"    - {name}" for name in exposed_binary_names)
        output.extend(
            f"    - {RED(name)} (symlink missing or pointing to unexpected location)"
            for name in unavailable_binary_names
        )
        if new_install and (exposed_man_pages or unavailable_man_pages):
            output.append("  These manual pages are now available")
        output.extend(f"    - {name}" for name in exposed_man_pages)
        output.extend(
            f"    - {RED(name)} (symlink missing or pointing to unexpected location)" for name in unavailable_man_pages
        )
    else:
        output.append("    apps and manual pages are not exposed")
    if include_injected and (injected_packages := venv.pipx_metadata.injected_packages):
        output.append("    Injected Packages:")
        output.extend(f"      - {name} {injected_packages[name].package_version}" for name in injected_packages)
    return "\n".join(output)


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
    exposed_binary_names: Final[list[str]] = sorted(
        path.name
        for path in get_exposed_paths_for_package(venv.bin_path, paths.CTX.bin_dir, group_app_paths(resource_packages))
    )
    unavailable_binary_names: Final[list[str]] = sorted({
        add_suffix(name, package_metadata.suffix)
        for name in package_metadata.apps
        if not exposed_app_names(name, package_metadata.suffix) & set(exposed_binary_names)
    })
    man_paths: Final[list[Path]] = [path for metadata in resource_packages for path in metadata.man_paths_to_expose]
    exposed_man_pages: Final[list[str]] = sorted(
        str(Path(path.parent.name) / path.name)
        for man_section in MAN_SECTIONS
        for path in get_exposed_man_paths_for_package(
            venv.man_path / man_section, paths.CTX.man_dir / man_section, man_paths
        )
    )
    unavailable_man_pages: Final[list[str]] = sorted(set(package_metadata.man_pages) - set(exposed_man_pages))
    return exposed_binary_names, unavailable_binary_names, exposed_man_pages, unavailable_man_pages


def _warn_if_not_on_path(local_bin_dir: Path) -> OutputMessage | None:
    if not userpath.in_current_path(str(local_bin_dir)):
        return OutputMessage(
            text=pipx_wrap(
                f"""
                {HAZARD}  Note: '{local_bin_dir}' is not on your PATH
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


def validate_expected_apps(venv: Venv, package_name: str, expected_apps: Sequence[str]) -> None:
    if not expected_apps:
        return

    package: Final[PackageInfo] = venv.package_metadata[package_name]
    available_apps: Final[list[str]] = sorted({
        app[:-4] if WINDOWS and app.lower().endswith(".exe") else app for app in package.apps_to_expose
    })
    if missing_apps := sorted(set(expected_apps) - set(available_apps)):
        msg: Final[str] = (
            f"Package {package_name} does not provide expected {'app' if len(missing_apps) == 1 else 'apps'} "
            f"{', '.join(missing_apps)}. "
            f"Available apps: {', '.join(available_apps) or 'none'}."
        )
        raise PipxError(msg)


def validate_suffix(suffix: str) -> str:
    # pipx splices a suffix straight into an exposed file name, so anything but a portable character set could steer the
    # destination out of PIPX_BIN_DIR or PIPX_MAN_DIR
    if re.fullmatch(r"[A-Za-z0-9._@+-]*", suffix) is None:
        msg: Final[str] = (
            f"Invalid suffix {suffix!r}. Use only letters, digits, and the characters . _ - + @ so exposed file "
            f"names stay inside pipx's directories."
        )
        raise PipxError(msg)
    return suffix


def locked_package_message(package_name: str) -> str:
    return f"Not upgrading locked package {package_name}. Update its lock file and run `pipx reinstall {package_name}`."


def get_venv_package_infos(venv: Venv) -> tuple[PackageInfo, ...] | None:
    if venv.pipx_metadata.main_package.package is not None:
        return tuple(venv.package_metadata.values())
    if not venv.python_path.is_file():
        return None
    try:
        venv_metadata: Final[VenvMetadata] = venv.get_venv_metadata_for_package(venv.root.name, set())
    except PipxError as error:
        # an environment that cannot report its packages is still removable, from the links that point into it
        _LOGGER.warning("%s  Unable to inspect %s, removing it anyway: %s", HAZARD, venv.name, error)
        return None
    return (
        PackageInfo(
            package=venv.root.name,
            package_or_url="",
            pip_args=[],
            include_apps=True,
            include_dependencies=False,
            apps=venv_metadata.apps,
            app_paths=venv_metadata.app_paths,
            apps_of_dependencies=venv_metadata.apps_of_dependencies,
            app_paths_of_dependencies=venv_metadata.app_paths_of_dependencies,
            man_pages=venv_metadata.man_pages,
            man_paths=venv_metadata.man_paths,
            man_pages_of_dependencies=venv_metadata.man_pages_of_dependencies,
            man_paths_of_dependencies=venv_metadata.man_paths_of_dependencies,
            package_version=venv_metadata.package_version,
            suffix="",
        ),
    )


def get_venv_resource_paths(
    resource_type: Literal["app", "man", "completion"],
    venv_resource_path: Path,
    local_resource_dir: Path,
    package_infos: tuple[PackageInfo, ...] | None,
) -> set[Path]:
    if package_infos is not None:
        get_package_resource_paths: Final[Callable[[PackageInfo, Path, Path], set[Path]]] = {
            "app": get_package_bin_dir_app_paths,
            "man": get_package_man_paths,
            "completion": get_package_completion_paths,
        }[resource_type]
        return set().union(
            *(
                get_package_resource_paths(package_info, venv_resource_path, local_resource_dir)
                for package_info in package_infos
            )
        )

    # without metadata, pipx infers ownership from link targets
    if not local_resource_dir.is_dir() or not can_symlink(local_resource_dir):
        return set()
    return get_exposed_paths_for_package(venv_resource_path, local_resource_dir)


def get_package_bin_dir_app_paths(package_info: PackageInfo, venv_bin_path: Path, local_bin_dir: Path) -> set[Path]:
    return get_exposed_paths_for_package(venv_bin_path, local_bin_dir, group_app_paths((package_info,)))


def get_package_man_paths(package_info: PackageInfo, venv_man_path: Path, local_man_dir: Path) -> set[Path]:
    return get_exposed_man_paths_for_package(venv_man_path, local_man_dir, package_info.man_paths_to_expose)


def get_package_completion_paths(
    package_info: PackageInfo,
    venv_completion_path: Path,
    local_completion_dir: Path,
) -> set[Path]:
    return get_exposed_paths_for_package(
        venv_completion_path,
        local_completion_dir,
        group_resource_paths((path.name, path) for path in package_info.completion_paths_to_expose),
    )


__all__ = [
    "VenvProblems",
    "add_suffix",
    "can_symlink",
    "drop_copies_claimed_elsewhere",
    "drop_links_taken_over",
    "expose_package_resources",
    "expose_resources_globally",
    "expose_shared_resources_in_order",
    "exposed_app_names",
    "force_replaces_only",
    "get_expected_venv_resource_paths",
    "get_exposed_man_paths_for_package",
    "get_exposed_paths_for_package",
    "get_package_bin_dir_app_paths",
    "get_package_completion_paths",
    "get_package_man_paths",
    "get_venv_package_infos",
    "get_venv_resource_paths",
    "get_venv_summary",
    "give_back_shared_links",
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
