import json
import os
import re
import subprocess
import sys
from pathlib import Path
from shutil import which
from typing import Any, Dict, List, Optional
from unittest import mock

from packaging.utils import canonicalize_name

from pipx import constants, main, pipx_metadata_file

WIN = sys.platform.startswith("win")

MOCK_PIPXMETADATA_0_1: Dict[str, Any] = {
    "main_package": None,
    "python_version": None,
    "venv_args": [],
    "injected_packages": {},
    "pipx_metadata_version": "0.1",
}

MOCK_PACKAGE_INFO_0_1: Dict[str, Any] = {
    "package": None,
    "package_or_url": None,
    "pip_args": [],
    "include_dependencies": False,
    "include_apps": True,
    "apps": [],
    "app_paths": [],
    "apps_of_dependencies": [],
    "app_paths_of_dependencies": {},
    "package_version": "",
}


def app_name(app: str) -> str:
    return f"{app}.exe" if WIN else app


def run_pipx_cli(pipx_args: List[str]) -> int:
    with mock.patch.object(sys, "argv", ["pipx"] + pipx_args):
        return main.cli()


def which_python(python_exe: str) -> Optional[str]:
    try:
        pyenv_which = subprocess.run(
            ["pyenv", "which", python_exe],
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )
    except FileNotFoundError:
        # no pyenv on system
        return which(python_exe)

    if pyenv_which.returncode == 0:
        return pyenv_which.stdout.strip()
    else:
        # pyenv on system, but pyenv has no path to python_exe
        return None


def unwrap_log_text(log_text: str):
    """Remove line-break + indent space from log messages

    Captured log lines always start with the 'severity' so if a line starts
    with any spaces assume it is due to an indented pipx wrapped message.
    """

    return re.sub(r"\n\s+", " ", log_text)


def _mock_legacy_package_info(
    modern_package_info: Dict[str, Any], metadata_version: str
) -> Dict[str, Any]:
    if metadata_version == "0.1":
        mock_package_info_template = MOCK_PACKAGE_INFO_0_1
    else:
        raise Exception(
            f"Internal Test Error: Unknown metadata_version={metadata_version}"
        )

    mock_package_info = {}
    for key in mock_package_info_template:
        mock_package_info[key] = modern_package_info[key]

    return mock_package_info


def mock_legacy_venv(venv_name: str, metadata_version: Optional[str] = None) -> None:
    """Convert a venv installed with the most recent pipx to look like
    one with a previous metadata version.
    metadata_version=None refers to no metadata file (pipx pre-0.15.0.0)
    """
    venv_dir = Path(constants.PIPX_LOCAL_VENVS) / canonicalize_name(venv_name)

    if metadata_version is None:
        os.remove(venv_dir / "pipx_metadata.json")
        return

    modern_metadata = pipx_metadata_file.PipxMetadata(venv_dir).to_dict()

    if metadata_version == "0.1":
        mock_pipx_metadata_template = MOCK_PIPXMETADATA_0_1
    else:
        raise Exception(
            f"Internal Test Error: Unknown metadata_version={metadata_version}"
        )

    # Convert to mock old metadata
    mock_pipx_metadata = {}
    for key in mock_pipx_metadata_template:
        if key == "main_package":
            mock_pipx_metadata[key] = _mock_legacy_package_info(
                modern_metadata[key], metadata_version=metadata_version
            )
        if key == "injected_packages":
            mock_pipx_metadata[key] = {}
            for injected in modern_metadata[key]:
                mock_pipx_metadata[key][injected] = _mock_legacy_package_info(
                    modern_metadata[key][injected], metadata_version=metadata_version
                )
        else:
            mock_pipx_metadata[key] = modern_metadata[key]
    mock_pipx_metadata["pipx_metadata_version"] = mock_pipx_metadata_template[
        "pipx_metadata_version"
    ]

    # replicate pipx_metadata_file.PipxMetadata.write()
    with open(venv_dir / "pipx_metadata.json", "w") as pipx_metadata_fh:
        json.dump(
            mock_pipx_metadata,
            pipx_metadata_fh,
            indent=4,
            sort_keys=True,
            cls=pipx_metadata_file.JsonEncoderHandlesPath,
        )
