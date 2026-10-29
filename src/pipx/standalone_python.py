from __future__ import annotations

__lazy_modules__ = [
    "datetime",
    "functools",
    "hashlib",
    "json",
    "pathlib",
    "pipx",
    "pipx.util",
    "platform",
    "re",
    "shutil",
    "tarfile",
    "urllib.request",
]

import datetime as dt
import hashlib
import http.client
import json
import logging
import os
import platform
import re
import shutil
import tarfile
import time
import urllib.error
from contextlib import contextmanager
from functools import partial
from http import HTTPStatus
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Final, TypedDict, cast
from urllib.request import Request, urlopen

from pipx import constants, paths
from pipx.animate import animate
from pipx.util import PipxError

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import TypeIs

    from filelock import BaseFileLock

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# much of this module comes from https://github.com/tusharsadhwani/yen/blob/main/src/yen/github.py

MACHINE_SUFFIX: Final[dict[str, dict[str, list[str] | dict[str, list[str]]]]] = {
    "Darwin": {
        "arm64": ["aarch64-apple-darwin-install_only.tar.gz"],
        "x86_64": ["x86_64-apple-darwin-install_only.tar.gz"],
    },
    "Linux": {
        "aarch64": {
            "glibc": ["aarch64-unknown-linux-gnu-install_only.tar.gz"],
            # no musl build exists for aarch64
        },
        "x86_64": {
            "glibc": [
                "x86_64_v3-unknown-linux-gnu-install_only.tar.gz",
                "x86_64-unknown-linux-gnu-install_only.tar.gz",
            ],
            "musl": ["x86_64_v3-unknown-linux-musl-install_only.tar.gz"],
        },
    },
    "Windows": {
        "AMD64": ["x86_64-pc-windows-msvc-install_only.tar.gz"],
        "ARM64": ["aarch64-pc-windows-msvc-install_only.tar.gz"],
    },
}

GITHUB_API_URL: Final[str] = "https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"
_URL_OPEN_TIMEOUT: Final[float] = 30
# GitHub can also drop the connection mid-response (RemoteDisconnected is a ConnectionError, a truncated chunked body
# an IncompleteRead), so failures while reading the body are as retryable as ones while opening the connection.
_TRANSIENT_NETWORK_ERRORS: Final[tuple[type[Exception], ...]] = (
    urllib.error.URLError,
    http.client.IncompleteRead,
    ConnectionError,
    TimeoutError,
)


def download_python_build_standalone(python_version: str, *, override: bool = False) -> str:
    # accept a command name such as python3.10 as well as the bare version 3.10
    python_version = re.sub(r"[c]?python", "", python_version)
    # the version names the cache directory that a failed attempt is cleared from below, so a path, "." or ".." would
    # point that rmtree outside the cache; one to three numeric parts is all resolve_python_version can match anyway
    if not re.fullmatch(r"[0-9]+(\.[0-9]+){0,2}", python_version):
        msg = f"Cannot fetch a standalone python build for {python_version!r}: expected a version such as '3.13'."
        raise PipxError(msg)

    install_dir: Final[Path] = paths.CTX.standalone_python_cachedir / python_version
    installed_python: Final[Path] = install_dir / "python.exe" if constants.WINDOWS else install_dir / "bin" / "python3"

    if not override and installed_python.exists():
        return str(installed_python)

    # the staging and backup directories of the swap are named after the version, and whatever already has those names
    # is cleared as a leftover, so a second pipx fetching this version must wait instead of deleting a live copy
    with _version_lock(install_dir):
        if not override and installed_python.exists():
            # another pipx installed this version while this one waited for the lock
            return str(installed_python)
        if not override and install_dir.exists():
            # a leftover directory without a usable interpreter is a failed prior attempt with nothing to preserve, so
            # clear it now; an override upgrade keeps its working install until the atomic swap below
            _LOGGER.warning("A previous attempt to install python %s failed. Retrying.", python_version)
            shutil.rmtree(install_dir)

        full_version, (download_link, digest) = resolve_python_version(python_version)

        with _staging_dir(install_dir) as staging_dir:
            archive: Final[Path] = staging_dir / f"python-{full_version}.tar.gz"
            download_dir: Final[Path] = staging_dir / "download"

            _download(full_version, download_link, archive)
            _unpack(full_version, archive, download_dir, digest)
            # the python installation we want is nested in the tarball under a directory named 'python'; only after it
            # is fully extracted do we swap it into place, so a failed download or unpack never destroys a working
            # interpreter
            _install_atomically(download_dir / "python", install_dir)

    return str(installed_python)


def _version_lock(install_dir: Path) -> BaseFileLock:
    from filelock import FileLock  # ruff:ignore[import-outside-top-level]  # pulls in asyncio, slows startup

    install_dir.parent.mkdir(parents=True, exist_ok=True)
    return FileLock(install_dir.with_name(f".{install_dir.name}.lock"))


def resolve_python_version(requested_version: str) -> tuple[str, tuple[str, str]]:
    requested_release: Final[list[str]] = requested_version.split(".")

    for full_version, download_link in list_pythons().items():
        if requested_release == full_version.split(".")[: len(requested_release)]:
            return full_version, download_link

    msg = f"Unable to acquire a standalone python build matching {requested_version}."
    raise PipxError(msg)


def list_pythons(*, use_cache: bool = True) -> dict[str, tuple[str, str]]:
    system, machine = platform.system(), platform.machine()
    try:
        download_link_suffixes = MACHINE_SUFFIX[system][machine]
    except KeyError as error:
        msg = f"No standalone Python builds are available for {system} on {machine}."
        raise PipxError(msg) from error

    # Linux entries nest their suffixes by libc
    if isinstance(download_link_suffixes, dict):
        # libc_ver() finds no glibc version on a musl system
        libc_version: Final[str] = platform.libc_ver()[0] or "musl"
        try:
            download_link_suffixes = download_link_suffixes[libc_version]
        except KeyError as error:
            msg = f"No standalone Python builds are available for {system} on {machine} with {libc_version}."
            raise PipxError(msg) from error

    python_releases: Final[list[tuple[str, str]]] = get_or_update_index(use_cache=use_cache)["releases"]

    python_versions: Final[dict[str, tuple[str, str]]] = {}
    # suffixes are in order of preference, so the first link found for a version wins
    for download_link_suffix in download_link_suffixes:
        for link, digest in python_releases:
            if not link.endswith(download_link_suffix):
                continue
            if (match := re.search(r"cpython-(\d+\.\d+\.\d+)", link)) is None:
                msg = f"Could not parse a Python version from {link!r}."
                raise PipxError(msg)
            python_versions.setdefault(match[1], (link, digest))

    return {
        version: python_versions[version]
        for version in sorted(python_versions, key=lambda version: [int(k) for k in version.split(".")], reverse=True)
    }


def get_or_update_index(*, use_cache: bool = True) -> _PythonIndex:
    index_file: Final[Path] = paths.CTX.standalone_python_cachedir / "index.json"
    # a legacy URL-only index fails validation, and a current one is refreshed after 30 days
    if (
        use_cache
        and index_file.exists()
        and _is_valid_python_index(loaded := json.loads(index_file.read_text()))
        and dt.datetime.now(tz=dt.UTC) - dt.datetime.fromtimestamp(loaded["fetched"], tz=dt.UTC)
        <= dt.timedelta(days=30)
    ):
        return loaded
    releases: Final[list[tuple[str, str]]] = get_latest_python_releases()
    index: Final[_PythonIndex] = {"fetched": dt.datetime.now(tz=dt.UTC).timestamp(), "releases": releases}
    index_file.write_text(json.dumps(index))
    return index


class _PythonIndex(TypedDict):
    fetched: float
    releases: list[tuple[str, str]]


def _is_valid_python_index(index: object) -> TypeIs[_PythonIndex]:
    match index:
        case {"fetched": int() | float(), "releases": list() as releases}:
            link_and_digest: Final[int] = 2
            return all(
                isinstance(release, list | tuple)
                and len(release) == link_and_digest
                and all(isinstance(value, str) for value in release)
                for release in releases
            )
        case _:
            return False


def get_latest_python_releases() -> list[tuple[str, str]]:
    try:
        release_data: Final[dict[str, list[dict[str, str]]]] = _fetch_release_data()
    except _TRANSIENT_NETWORK_ERRORS as e:
        msg = f"Unable to fetch python-build-standalone release data (from {GITHUB_API_URL})."
        raise PipxError(msg) from e

    return [(asset["browser_download_url"], asset["digest"]) for asset in release_data["assets"]]


def _fetch_release_data() -> dict[str, list[dict[str, str]]]:
    attempt = 0
    while True:
        attempt += 1
        try:
            # the index body is small, so unlike the archive download a retry re-fetches it whole
            with urlopen(GITHUB_API_URL, timeout=_URL_OPEN_TIMEOUT) as response:
                return cast("dict[str, list[dict[str, str]]]", json.load(response))
        except _TRANSIENT_NETWORK_ERRORS as error:
            _backoff_or_raise(error, attempt, GITHUB_API_URL)


def _backoff_or_raise(error: Exception, attempt: int, url: str) -> None:
    fetch_attempts: Final[int] = 3
    # GitHub's release CDN answers with transient 5xx (and 429 under rate limiting) often enough that a single failure
    # should not abort a download; these statuses are safe to retry, unlike a 404 for a missing build
    retryable: Final[bool] = not isinstance(error, urllib.error.HTTPError) or error.code in {429, 500, 502, 503, 504}
    if not retryable or attempt >= fetch_attempts:
        raise error
    _LOGGER.debug("fetch attempt %d/%d for %s failed (%s); retrying", attempt, fetch_attempts, url, error)
    time.sleep(0.5 * 2 ** (attempt - 1))


@contextmanager
def _staging_dir(install_dir: Path) -> Generator[Path]:
    # unpack next to install_dir rather than in the system temp dir: from a tmpfs /tmp or another btrfs subvolume,
    # moving the build into place copies all of it and splits its hard links into separate files; the dot prefix hides
    # a fetch in progress from interpreter list, prune and upgrade
    staging_dir: Final[Path] = install_dir.with_name(f".{install_dir.name}.incoming")
    # under the version lock, anything already at this name is a killed fetch's leftover
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    # owner-only like a system temp dir; mkdir fails rather than unpack into a directory created here since the cleanup
    staging_dir.mkdir(mode=0o700)
    try:
        yield staging_dir
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)


def _download(full_version: str, download_link: str, archive: Path) -> None:
    with animate(f"Downloading python {full_version} build", do_animation=True):
        try:
            _download_resuming(download_link, archive)
        except _TRANSIENT_NETWORK_ERRORS as e:
            msg = f"Unable to download python {full_version} build."
            raise PipxError(msg) from e


def _download_resuming(url: str, archive: Path) -> None:
    archive.touch()
    attempt = 0
    while True:
        attempt += 1
        with archive.open("r+b") as file_handle:
            written = file_handle.seek(0, os.SEEK_END)
            # url comes from the pinned GitHub release index; a build archive is ~32MB, so on a dropped connection ask
            # the CDN to continue from the bytes already on disk instead of downloading everything again
            request = Request(url, headers={"Range": f"bytes={written}-"} if written else {})  # ruff:ignore[suspicious-url-open-usage]
            try:
                with urlopen(request, timeout=_URL_OPEN_TIMEOUT) as response:  # ruff:ignore[suspicious-url-open-usage]
                    if written and response.status != HTTPStatus.PARTIAL_CONTENT:
                        # the server ignored the range request and answered with the whole file
                        file_handle.seek(0)
                        file_handle.truncate()
                    # 32KB chunks keep memory flat
                    file_handle.writelines(iter(partial(response.read, 32768), b""))
            except _TRANSIENT_NETWORK_ERRORS as error:
                _backoff_or_raise(error, attempt, url)
            else:
                return


def _unpack(full_version: str, archive: Path, download_dir: Path, expected_checksum: str) -> None:
    with animate(f"Unpacking python {full_version} build", do_animation=True):
        sha256_hash: Final = hashlib.sha256()
        with Path(archive).open("rb") as python_zip:
            for chunk in iter(lambda: python_zip.read(32768), b""):
                sha256_hash.update(chunk)

        if (checksum := f"sha256:{sha256_hash.hexdigest()}") != expected_checksum:
            msg = f"Checksum mismatch for python {full_version} build. Expected {expected_checksum}, got {checksum}."
            raise PipxError(msg)

        try:
            with tarfile.open(archive, mode="r:gz") as tar:
                if hasattr(tarfile, "data_filter"):
                    tar.extractall(download_dir, filter="data")
                else:
                    # Python 3.11.0-3.11.3 predate tarfile's data filter, so validate and extract by hand
                    _extract_safely(tar, download_dir)
        except tarfile.TarError as error:
            msg = f"Unable to unpack python {full_version} build."
            raise PipxError(msg) from error


def _extract_safely(tar: tarfile.TarFile, dest: Path) -> None:
    root: Final[Path] = dest.resolve()
    for member in tar.getmembers():
        if member.isdev():
            continue  # the data filter drops device, block, and fifo entries
        _reject_escape(member, root)
        _extract_member(tar, member, dest)


def _reject_escape(member: tarfile.TarInfo, root: Path) -> None:
    # like the data filter, extract under normalized names: "dir/.." leads elsewhere as soon as "dir" is a link
    member.name = os.path.normpath(member.name)
    if _escapes(root, root / member.name):
        msg = f"Refusing to extract {member.name!r} outside the download directory."
        raise PipxError(msg)
    if member.issym() or member.islnk():
        member.linkname = os.path.normpath(member.linkname)
        base: Final[Path] = root if member.islnk() else (root / member.name).parent
        # a hard link to a symlink re-creates that symlink, and so its relative target, at another depth
        relocates_symlink: Final[bool] = member.islnk() and (root / member.linkname).is_symlink()
        if PurePosixPath(member.linkname).is_absolute() or relocates_symlink or _escapes(root, base / member.linkname):
            msg = f"Refusing to extract link {member.name!r} pointing outside the download directory."
            raise PipxError(msg)


def _escapes(root: Path, target: Path) -> bool:
    # members are extracted one at a time, so resolve the links unpacked so far for as much of the path as exists
    for existing in (target, *target.parents):
        try:
            # strict: a lenient realpath takes a link it cannot follow (a loop, an overlong chain) for a directory
            followed = os.path.realpath(existing, strict=True)
        except FileNotFoundError:
            continue
        except OSError:
            return True
        resolved = Path(os.path.normpath(Path(followed, target.relative_to(existing))))
        return resolved != root and root not in resolved.parents
    return True  # pragma: no cover  # target is below root, which exists, so the loop always returns


def _extract_member(tar: tarfile.TarFile, member: tarfile.TarInfo, dest: Path) -> None:
    target: Final[Path] = dest / member.name
    if member.isdir():
        target.mkdir(parents=True, exist_ok=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() or target.exists():
        target.unlink()
    if member.issym():
        target.symlink_to(member.linkname)
    elif member.islnk():
        os.link(dest / member.linkname, target)
    else:
        source: Final = tar.extractfile(member)
        with target.open("wb") as handle:
            if source is not None:
                shutil.copyfileobj(source, handle)
        target.chmod(member.mode & 0o777)  # drop setuid, setgid, and sticky bits like the data filter


def _install_atomically(source: Path, install_dir: Path) -> None:
    backup_dir: Final[Path] = install_dir.with_name(f".{install_dir.name}.previous")
    if backup_dir.exists():
        shutil.rmtree(backup_dir)

    if replaced_existing := install_dir.exists():
        install_dir.replace(backup_dir)
    try:
        source.replace(install_dir)
    except OSError:
        if replaced_existing:
            backup_dir.replace(install_dir)
        raise
    if replaced_existing:
        shutil.rmtree(backup_dir, ignore_errors=True)


__all__ = [
    "GITHUB_API_URL",
    "MACHINE_SUFFIX",
    "download_python_build_standalone",
    "get_latest_python_releases",
    "get_or_update_index",
    "list_pythons",
    "resolve_python_version",
]
