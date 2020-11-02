import sys
from typing import Dict, List
from unittest import mock

from pipx import main

# Versions of all packages possibly used in our tests
PKGSPEC: Dict[str, str] = {
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
    "lektor": "lektor==3.2.0",
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
    "retext": "retext==7.1.0",
    "robotframework": "robotframework==3.2.2",
    "shell-functools": "shell-functools==0.3.0",
    "speedtest-cli": "speedtest-cli==2.1.2",
    "sphinx": "sphinx==3.2.1",
    "sqlmap": "sqlmap==1.4.10",
    "streamlink": "streamlink==1.7.0",
    "taguette": "taguette==0.9.2",
    "term2048": "term2048==0.2.7",
    "tox-ini-fmt": "tox-ini-fmt==0.5.0",
    "visidata": "visidata==2.0.1",
    "vulture": "vulture==2.1",
    "weblate": "weblate==4.3.1",  # py3.9 FAIL lxml<4.7.0,>=
    "youtube-dl": "youtube-dl==2020.9.20",
    "zeo": "zeo==5.2.2",
}


def run_pipx_cli(pipx_args: List[str]) -> int:
    with mock.patch.object(sys, "argv", ["pipx"] + pipx_args):
        return main.cli()
