import datetime
import hashlib
import json
import logging
import os
import platform
import re
import shutil
import tarfile
import tempfile
import urllib.error
from functools import partial
from pathlib import Path, PurePosixPath
from typing import Any, Final
from urllib.request import urlopen

from pipx import constants, paths
from pipx.animate import animate
from pipx.util import PipxError

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Much of the code in this module is adapted with extreme gratitude from
# https://github.com/tusharsadhwani/yen/blob/main/src/yen/github.py

MACHINE_SUFFIX: Final[dict[str, dict[str, Any]]] = {
    "Darwin": {
        "arm64": ["aarch64-apple-darwin-install_only.tar.gz"],
        "x86_64": ["x86_64-apple-darwin-install_only.tar.gz"],
    },
    "Linux": {
        "aarch64": {
            "glibc": ["aarch64-unknown-linux-gnu-install_only.tar.gz"],
            # musl doesn't exist
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
PYTHON_VERSION_REGEX: Final[re.Pattern[str]] = re.compile(r"cpython-(\d+\.\d+\.\d+)")
_URL_OPEN_TIMEOUT: Final[float] = 30


def download_python_build_standalone(python_version: str, override: bool = False):
    """When all other python executable resolutions have failed,
    attempt to download and use an appropriate python build
    from https://github.com/astral-sh/python-build-standalone
    and unpack it into the pipx shared directory."""

    # python_version can be a bare version number like "3.10" or a "binary name" like python3.10
    # we'll convert it to a bare version number
    python_version = re.sub(r"[c]?python", "", python_version)

    install_dir = paths.ctx.standalone_python_cachedir / python_version
    installed_python = install_dir / "python.exe" if constants.WINDOWS else install_dir / "bin" / "python3"

    if not override and installed_python.exists():
        return str(installed_python)
    if not override and install_dir.exists():
        # a leftover directory without a usable interpreter is a failed prior attempt with nothing to preserve, so clear
        # it now; an override upgrade keeps its working install until the atomic swap below
        _LOGGER.warning(f"A previous attempt to install python {python_version} failed. Retrying.")
        shutil.rmtree(install_dir)

    full_version, (download_link, digest) = resolve_python_version(python_version)

    with tempfile.TemporaryDirectory() as tempdir:
        archive = Path(tempdir) / f"python-{full_version}.tar.gz"
        download_dir = Path(tempdir) / "download"

        # download the python build gz
        _download(full_version, download_link, archive)

        # unpack the python build
        _unpack(full_version, download_link, archive, download_dir, digest)

        # the python installation we want is nested in the tarball under a directory named 'python'; only after it is
        # fully extracted do we swap it into place, so a failed download or unpack never destroys a working interpreter
        _install_atomically(download_dir / "python", install_dir)

    return str(installed_python)


def _install_atomically(source: Path, install_dir: Path) -> None:
    install_dir.parent.mkdir(parents=True, exist_ok=True)
    # stage on the same filesystem as install_dir so the swap-in is an atomic rename rather than a mid-copy window
    staging_dir = install_dir.with_name(f".{install_dir.name}.incoming")
    backup_dir = install_dir.with_name(f".{install_dir.name}.previous")
    for leftover in (staging_dir, backup_dir):
        if leftover.exists():
            shutil.rmtree(leftover)

    shutil.move(str(source), str(staging_dir))
    replaced_existing = install_dir.exists()
    if replaced_existing:
        os.replace(install_dir, backup_dir)
    try:
        os.replace(staging_dir, install_dir)
    except OSError:
        if replaced_existing:
            os.replace(backup_dir, install_dir)
        raise
    if replaced_existing:
        shutil.rmtree(backup_dir, ignore_errors=True)


def _download(full_version: str, download_link: str, archive: Path):
    with animate(f"Downloading python {full_version} build", True):
        try:
            # python standalone builds are typically ~32MB in size. to avoid
            # ballooning memory usage, we read the file in chunks
            with urlopen(download_link, timeout=_URL_OPEN_TIMEOUT) as response, open(archive, "wb") as file_handle:
                for data in iter(partial(response.read, 32768), b""):
                    file_handle.write(data)
        except urllib.error.URLError as e:
            raise PipxError(f"Unable to download python {full_version} build.") from e


def _unpack(full_version, download_link, archive: Path, download_dir: Path, expected_checksum: str):
    with animate(f"Unpacking python {full_version} build", True):
        # Calculate checksum efficiently
        sha256_hash = hashlib.sha256()
        with open(archive, "rb") as python_zip:
            # Read in chunks to avoid loading the whole file into memory
            for chunk in iter(lambda: python_zip.read(32768), b""):
                sha256_hash.update(chunk)

        checksum = "sha256:" + sha256_hash.hexdigest()

        # Validate checksum
        if checksum != expected_checksum:
            raise PipxError(
                f"Checksum mismatch for python {full_version} build. Expected {expected_checksum}, got {checksum}."
            )

        try:
            with tarfile.open(archive, mode="r:gz") as tar:
                if hasattr(tarfile, "data_filter"):
                    tar.extractall(download_dir, filter="data")
                else:
                    # Python 3.10.0-3.10.11 predate tarfile's data filter, so validate and extract by hand
                    _extract_safely(tar, download_dir)
        except tarfile.TarError as error:
            raise PipxError(f"Unable to unpack python {full_version} build.") from error


def _extract_safely(tar: tarfile.TarFile, dest: Path) -> None:
    root: Final[Path] = dest.resolve()
    for member in tar.getmembers():
        if member.isdev():
            continue  # the data filter drops device, block, and fifo entries
        _reject_escape(member, root)
        _extract_member(tar, member, dest)


def _reject_escape(member: tarfile.TarInfo, root: Path) -> None:
    if _escapes(root, root / member.name):
        raise PipxError(f"Refusing to extract {member.name!r} outside the download directory.")
    if member.issym() or member.islnk():
        link: Final[PurePosixPath] = PurePosixPath(member.linkname)
        base: Final[Path] = root if member.islnk() else (root / member.name).parent
        if link.is_absolute() or _escapes(root, base / member.linkname):
            raise PipxError(f"Refusing to extract link {member.name!r} pointing outside the download directory.")


def _escapes(root: Path, target: Path) -> bool:
    resolved: Final[Path] = Path(os.path.normpath(target))
    return resolved != root and root not in resolved.parents


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
        source = tar.extractfile(member)
        with target.open("wb") as handle:
            if source is not None:
                shutil.copyfileobj(source, handle)
        target.chmod(member.mode & 0o777)  # drop setuid, setgid, and sticky bits like the data filter


def _is_valid_python_index(index: Any) -> bool:
    if not isinstance(index, dict):
        return False

    fetched = index.get("fetched")
    releases = index.get("releases")
    if not isinstance(fetched, int | float) or not isinstance(releases, list):
        return False

    return all(
        isinstance(release, (list, tuple)) and len(release) == 2 and all(isinstance(value, str) for value in release)
        for release in releases
    )


def get_or_update_index(use_cache: bool = True):
    """Get or update the index of available python builds from
    the python-build-standalone repository."""
    index_file = paths.ctx.standalone_python_cachedir / "index.json"
    if use_cache and index_file.exists():
        index = json.loads(index_file.read_text())
        # Refresh legacy URL-only indexes, and update current indexes after 30 days.
        if _is_valid_python_index(index):
            fetched = datetime.datetime.fromtimestamp(index["fetched"])
            if datetime.datetime.now() - fetched > datetime.timedelta(days=30):
                index = {}
        else:
            index = {}
    else:
        index = {}
    if not index:
        releases = get_latest_python_releases()
        index = {"fetched": datetime.datetime.now().timestamp(), "releases": releases}
        # update index
        index_file.write_text(json.dumps(index))
    return index


def get_latest_python_releases() -> list[tuple[str, str]]:
    """Returns the list of python download links from the latest github release."""
    try:
        with urlopen(GITHUB_API_URL, timeout=_URL_OPEN_TIMEOUT) as response:
            release_data = json.load(response)

    except urllib.error.URLError as e:
        # raise
        raise PipxError(f"Unable to fetch python-build-standalone release data (from {GITHUB_API_URL}).") from e

    return [(asset["browser_download_url"], asset["digest"]) for asset in release_data["assets"]]


def list_pythons(use_cache: bool = True) -> dict[str, tuple[str, str]]:
    """Returns available python versions for your machine and their download links."""
    system, machine = platform.system(), platform.machine()
    try:
        download_link_suffixes = MACHINE_SUFFIX[system][machine]
    except KeyError as error:
        raise PipxError(f"No standalone Python builds are available for {system} on {machine}.") from error

    # linux suffixes are nested under glibc or musl builds
    if system == "Linux":
        # fallback to musl if libc version is not found
        libc_version = platform.libc_ver()[0] or "musl"
        try:
            download_link_suffixes = download_link_suffixes[libc_version]
        except KeyError as error:
            raise PipxError(
                f"No standalone Python builds are available for {system} on {machine} with {libc_version}."
            ) from error

    python_releases = get_or_update_index(use_cache)["releases"]

    available_python_links = [
        (link, digest)
        # Suffixes are in order of preference.
        for download_link_suffix in download_link_suffixes
        for link, digest in python_releases
        if link.endswith(download_link_suffix)
    ]

    python_versions: dict[str, tuple[str, str]] = {}
    for link, digest in available_python_links:
        match = PYTHON_VERSION_REGEX.search(link)
        assert match is not None
        python_version = match[1]
        # Don't override already found versions, they are in order of preference
        if python_version in python_versions:
            continue

        python_versions[python_version] = link, digest

    return {
        version: python_versions[version]
        for version in sorted(
            python_versions,
            # sort by semver
            key=lambda version: [int(k) for k in version.split(".")],
            reverse=True,
        )
    }


def resolve_python_version(requested_version: str):
    pythons = list_pythons()
    requested_release = requested_version.split(".")

    for full_version, download_link in pythons.items():
        standalone_release = full_version.split(".")
        if requested_release == standalone_release[: len(requested_release)]:
            return full_version, download_link

    raise PipxError(f"Unable to acquire a standalone python build matching {requested_version}.")


__all__ = [
    "download_python_build_standalone",
    "get_latest_python_releases",
    "get_or_update_index",
    "list_pythons",
    "resolve_python_version",
]
