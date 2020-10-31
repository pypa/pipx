import json
import os
import subprocess
import sys
from pathlib import Path
from shutil import which
from typing import Any, Dict, List, Optional
from unittest import mock

from pipx import constants, main, pipx_metadata_file

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

# Versions of all packages possibly used in our tests
PKGSPEC: Dict[str, str] = {
    "lektor": "Lektor==3.2.0",
    "retext": "ReText==7.1.0",
    "sphinx": "Sphinx==3.2.1",
    "weblate": "Weblate==4.3.1",  # py3.9 FAIL lxml<4.7.0,>=
    "zeo": "ZEO==5.2.2",
    "ansible": "ansible==2.9.13",
    "awscli": "awscli==1.18.168",
    "b2": "b2==2.0.2",
    "beancount": "beancount==2.3.3",  # py3.9 FAIL lxml
    "beets": "beets==1.4.9",
    "black": "black==20.8b1",
    "cactus": "cactus==3.3.3",
    "chert": "chert==19.1.0",
    "cloudtoken": "cloudtoken==0.1.707",
    "coala": "coala==0.11.0",
    "cookiecutter": "cookiecutter==1.7.2",
    "cython": "cython==0.29.21",
    "datasette": "datasette==0.50.2",
    "diffoscope": "diffoscope==154",
    "doc2dash": "doc2dash==2.3.0",
    "doitlive": "doitlive==4.3.0",
    "gdbgui": "gdbgui==0.14.0.1",
    "gns3-gui": "gns3-gui==2.2.15",
    "grow": "grow==1.0.0a10",
    "guake": "guake==3.7.0",
    "gunicorn": "gunicorn==20.0.4",
    "howdoi": "howdoi==2.0.7",  # py3.9 FAIL lxml
    "httpie": "httpie==2.3.0",
    "hyde": "hyde==0.8.9",  # py3.9 FAIL pyyaml
    "ipython": "ipython==7.16.1",
    "isort": "isort==5.6.4",
    "jupyter": "jupyter==1.0.0",
    "kaggle": "kaggle==1.5.9",
    "kibitzr": "kibitzr==6.0.0",  # py3.9 FAIL lxml
    "klaus": "klaus==1.5.2",
    "kolibri": "kolibri==0.14.3",
    "localstack": "localstack==0.12.1",
    "mackup": "mackup==0.8.29",  # NOTE: ONLY FOR mac, linux
    "magic-wormhole": "magic-wormhole==0.12.0",
    "mayan-edms": "mayan-edms==3.5.2",  # py3.9 FAIL pillow==7.1.2
    "mkdocs": "mkdocs==1.1.2",
    "mycli": "mycli==1.22.2",
    "nikola": "nikola==8.1.1",  # py3.9 FAIL lxml>=3.3.5
    "nox": "nox==2020.8.22",
    "pelican": "pelican==4.5.0",
    "platformio": "platformio==5.0.1",
    "ppci": "ppci==0.5.8",
    "prosopopee": "prosopopee==1.1.3",
    "ptpython": "ptpython==3.0.7",
    "pycowsay": "pycowsay==0.0.0.1",
    "pylint": "pylint==2.3.1",
    "robotframework": "robotframework==3.2.2",
    "shell-functools": "shell-functools==0.3.0",
    "speedtest-cli": "speedtest-cli==2.1.2",
    "sqlmap": "sqlmap==1.4.10",
    "streamlink": "streamlink==1.7.0",
    "taguette": "taguette==0.9.2",
    "term2048": "term2048==0.2.7",
    "tox-ini-fmt": "tox-ini-fmt==0.5.0",
    "visidata": "visidata==2.0.1",
    "vulture": "vulture==2.1",
    "youtube-dl": "youtube-dl==2020.9.20",
}


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
    venv_dir = Path(constants.PIPX_LOCAL_VENVS) / venv_name

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
