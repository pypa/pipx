import json
import shutil
import platform
import re
import urllib.error
from typing import Any
from urllib.request import urlopen
import datetime
from functools import partial
import hashlib
import tarfile

from pipx.constants import PIPX_STANDALONE_PYTHON_CACHEDIR
from pipx.util import PipxError
from pipx.animate import animate

# Much of the code in this module is adapted with extreme gratitude from
# https://github.com/tusharsadhwani/yen/blob/main/src/yen/github.py

MACHINE_SUFFIX = {
    "Darwin": {
        "arm64": "aarch64-apple-darwin-install_only.tar.gz",
        "x86_64": "x86_64-apple-darwin-install_only.tar.gz",
    },
    "Linux": {
        "aarch64": {
            "glibc": "aarch64-unknown-linux-gnu-install_only.tar.gz",
            # musl doesn't exist
        },
        "x86_64": {
            "glibc": "x86_64_v3-unknown-linux-gnu-install_only.tar.gz",
            "musl": "x86_64_v3-unknown-linux-musl-install_only.tar.gz",
        },
    },
    "Windows": {"AMD64": "x86_64-pc-windows-msvc-shared-install_only.tar.gz"},
}

GITHUB_API_URL = (
    "https://api.github.com/repos/indygreg/python-build-standalone/releases/latest"
)
PYTHON_VERSION_REGEX = re.compile(r"cpython-(\d+\.\d+\.\d+)")


class NotAvailable(Exception):
    """Raised when the asked Python version is not available."""




def get_latest_python_releases() -> list[str]:
    """Returns the list of python download links from the latest github release."""
    try:
        with urlopen(GITHUB_API_URL) as response:
            release_data = json.load(response)

    except urllib.error.URLError as e:
        # raise
        raise PipxError("Unable to fetch python-build-standalone release data.") from e

    return [asset["browser_download_url"] for asset in release_data["assets"]]


def list_pythons() -> dict[str, str]:
    """Returns available python versions for your machine and their download links."""
    system, machine = platform.system(), platform.machine()
    download_link_suffix = MACHINE_SUFFIX[system][machine]
    # linux suffixes are nested under glibc or musl builds
    if system == "Linux":
        # fallback to musl if libc version is not found
        libc_version = platform.libc_ver()[0] or "musl"
        download_link_suffix = download_link_suffix[libc_version]

    python_releases = get_or_update_index()['releases']

    available_python_links = [
        link for link in python_releases if link.endswith(download_link_suffix)
    ]

    python_versions: dict[str, str] = {}
    for link in available_python_links:
        match = PYTHON_VERSION_REGEX.search(link)
        assert match is not None
        python_version = match[1]
        python_versions[python_version] = link

    sorted_python_versions = {
        version: python_versions[version]
        for version in sorted(
            python_versions,
            # sort by semver
            key=lambda version: [int(k) for k in version.split(".")],
            reverse=True,
        )
    }
    return sorted_python_versions

def resolve_python_version(requested_version: str):
    pythons = list_pythons()

    for version, version_download_link in pythons.items():
        if version.startswith(requested_version):
            python_version = version
            download_link = version_download_link
            break
    else:
        raise NotAvailable(f"Python version {requested_version} is not available.")

    return python_version, download_link
