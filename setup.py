#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

if sys.version_info < (3, 6, 0):
    print("Python 3.6+ is required")
    exit(1)
import io  # noqa E402
import os  # noqa E402
from setuptools import find_packages, setup  # noqa E402
from pathlib import Path  # noqa E402
from typing import List  # noqa E402
import ast  # noqa E402
import re  # noqa E402

CURDIR = Path(__file__).parent

EXCLUDE_FROM_PACKAGES = ["tests"]
REQUIRED: List[str] = ["userpath"]

with io.open(os.path.join(CURDIR, "README.md"), "r", encoding="utf-8") as f:
    README = f.read()


def get_version() -> str:
    main_file = CURDIR / "pipx" / "main.py"
    _version_re = re.compile(r"__version__\s+=\s+(?P<version>.*)")
    with open(main_file, "r", encoding="utf8") as f:
        match = _version_re.search(f.read())
        version = match.group("version") if match is not None else '"unknown"'
    return str(ast.literal_eval(version))


setup(
    name="pipx",
    version=get_version(),
    author="Chad Smith",
    author_email="grassfedcode@gmail.com",
    description="execute binaries from Python packages in isolated environments",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/pipxproject/pipx",
    license="License :: OSI Approved :: MIT License",
    packages=find_packages(exclude=EXCLUDE_FROM_PACKAGES),
    include_package_data=True,
    keywords=["pip", "install", "cli", "workflow", "Virtual Environment"],
    scripts=[],
    entry_points={"console_scripts": ["pipx = pipx.main:cli"]},
    extras_require={
        "dev": ["black", "flake8", "mypy", "jinja2", "mkdocs", "mkdocs-material"]
    },
    zip_safe=False,
    python_requires=">=3.6",
    install_requires=REQUIRED,
    test_suite="tests.test_pipx",
    classifiers=[
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3 :: Only",
    ],
)
