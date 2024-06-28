import datetime
import hashlib
import json
import logging
import platform
import re
import shutil
import tarfile
import tempfile
import urllib.error
from functools import partial
from pathlib import Path
from typing import Any, Dict, List
from urllib.request import urlopen

from pipx import constants, paths
from pipx.animate import animate
from pipx.util import PipxError

logger = logging.getLogger(__name__)

# Much of the code in this module is adapted with extreme gratitude from
# https://github.com/tusharsadhwani/yen/blob/main/src/yen/github.py

MACHINE_SUFFIX: Dict[str, Dict[str, Any]] = {
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
    "Windows": {"AMD64": ["x86_64-pc-windows-msvc-shared-install_only.tar.gz"]},
}

GITHUB_API_URL = "https://api.github.com/repos/indygreg/python-build-standalone/releases/latest"
PYTHON_VERSION_REGEX = re.compile(r"cpython-(\d+\.\d+\.\d+)")


def download_python_build_standalone(python_version: str, override: bool = False):
    """When all other python executable resolutions have failed,
    attempt to download and use an appropriate python build
    from https://github.com/indygreg/python-build-standalone
    and unpack it into the pipx shared directory."""

    # python_version can be a bare version number like "3.9" or a "binary name" like python3.10
    # we'll convert it to a bare version number
    python_version = re.sub(r"[c]?python", "", python_version)

    install_dir = paths.ctx.standalone_python_cachedir / python_version
    installed_python = install_dir / "python.exe" if constants.WINDOWS else install_dir / "bin" / "python3"

    if override:
        if install_dir.exists():
            shutil.rmtree(install_dir)
    else:
        if installed_python.exists():
            return str(installed_python)

        if install_dir.exists():
            logger.warning(f"A previous attempt to install python {python_version} failed. Retrying.")
            shutil.rmtree(install_dir)

    full_version, download_link = resolve_python_version(python_version)

    with tempfile.TemporaryDirectory() as tempdir:
        archive = Path(tempdir) / f"python-{full_version}.tar.gz"
        download_dir = Path(tempdir) / "download"

        # download the python build gz
        _download(full_version, download_link, archive)

        # unpack the python build
        _unpack(full_version, download_link, archive, download_dir)

        # the python installation we want is nested in the tarball
        # under a directory named 'python'. We move it to the install
        # directory
        extracted_dir = download_dir / "python"
        shutil.move(extracted_dir, install_dir)

    return str(installed_python)


def _download(full_version: str, download_link: str, archive: Path):
    with animate(f"Downloading python {full_version} build", True):
        try:
            # python standalone builds are typically ~32MB in size. to avoid
            # ballooning memory usage, we read the file in chunks
            with urlopen(download_link) as response, open(archive, "wb") as file_handle:
                for data in iter(partial(response.read, 32768), b""):
                    file_handle.write(data)
        except urllib.error.URLError as e:
            raise PipxError(f"Unable to download python {full_version} build.") from e


def _unpack(full_version, download_link, archive: Path, download_dir: Path):
    with animate(f"Unpacking python {full_version} build", True):
        # Calculate checksum
        with open(archive, "rb") as python_zip:
            checksum = hashlib.sha256(python_zip.read()).hexdigest()

        # Validate checksum
        checksum_link = download_link + ".sha256"
        expected_checksum = urlopen(checksum_link).read().decode().rstrip("\n")
        if checksum != expected_checksum:
            raise PipxError(
                f"Checksum mismatch for python {full_version} build. Expected {expected_checksum}, got {checksum}."
            )

        with tarfile.open(archive, mode="r:gz") as tar:
            tar.extractall(download_dir)


def get_or_update_index(use_cache: bool = True):
    """Get or update the index of available python builds from
    the python-build-standalone repository."""
    index_file = paths.ctx.standalone_python_cachedir / "index.json"
    if use_cache and index_file.exists():
        index = json.loads(index_file.read_text())
        # update index after 30 days
        fetched = datetime.datetime.fromtimestamp(index["fetched"])
        if datetime.datetime.now() - fetched > datetime.timedelta(days=30):
            index = {}
    else:
        index = {}
    if not index:
        releases = get_latest_python_releases()
        index = {"fetched": datetime.datetime.now().timestamp(), "releases": releases}
        # update index
        index_file.write_text(json.dumps(index))
    return index


def get_latest_python_releases() -> List[str]:
    """Returns the list of python download links from the latest github release."""
    try:
        with urlopen(GITHUB_API_URL) as response:
            release_data = json.load(response)

    except urllib.error.URLError as e:
        # raise
        raise PipxError(f"Unable to fetch python-build-standalone release data (from {GITHUB_API_URL}).") from e

    return [asset["browser_download_url"] for asset in release_data["assets"]]


def list_pythons(use_cache: bool = True) -> Dict[str, str]:
    """Returns available python versions for your machine and their download links."""
    system, machine = platform.system(), platform.machine()
    download_link_suffixes = MACHINE_SUFFIX[system][machine]
    # linux suffixes are nested under glibc or musl builds
    if system == "Linux":
        # fallback to musl if libc version is not found
        libc_version = platform.libc_ver()[0] or "musl"
        download_link_suffixes = download_link_suffixes[libc_version]

    python_releases = get_or_update_index(use_cache)["releases"]

    available_python_links = [
        link
        # Suffixes are in order of preference.
        for download_link_suffix in download_link_suffixes
        for link in python_releases
        if link.endswith(download_link_suffix)
    ]

    python_versions: dict[str, str] = {}
    for link in available_python_links:
        match = PYTHON_VERSION_REGEX.search(link)
        assert match is not None
        python_version = match[1]
        # Don't override already found versions, they are in order of preference
        if python_version in python_versions:
            continue

        python_versions[python_version] = link

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
