#!/usr/bin/env python3

import sys
from setuptools import find_packages, setup  # type: ignore

if sys.version_info < (3, 6, 0):
    sys.exit(
        "Python 3.6 or later is required. "
        "See https://github.com/pipxproject/pipx "
        "for installation instructions."
    )

from pathlib import Path  # noqa E402
from runpy import run_path  # noqa E402
from typing import List  # noqa E402
import ast  # noqa E402
import re  # noqa E402

CURDIR = Path(__file__).parent

REQUIRED = ["userpath", "argcomplete>=1.9.4, <2.0"]  # type: List[str]


def get_version():
    version_file = CURDIR.joinpath("src", "pipx", "version.py").resolve()
    namespace = run_path(str(version_file))
    return namespace["__version__"]


setup(
    name="pipx",
    version=get_version(),
    author="Chad Smith",
    author_email="grassfedcode@gmail.com",
    description="Install and Run Python Applications in Isolated Environments",
    long_description=CURDIR.joinpath("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/pipxproject/pipx",
    license="License :: OSI Approved :: MIT License",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    keywords=["pip", "install", "cli", "workflow", "Virtual Environment"],
    scripts=[],
    entry_points={"console_scripts": ["pipx = pipx.main:cli"]},
    zip_safe=False,
    install_requires=REQUIRED,
    test_suite="tests.test_pipx",
    classifiers=[
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3 :: Only",
    ],
    project_urls={
        "Documentation": "https://pipxproject.github.io/pipx/",
        "Source Code": "https://github.com/pipxproject/pipx",
        "Bug Tracker": "https://github.com/pipxproject/pipx/issues",
    },
)
