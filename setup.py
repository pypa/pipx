#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import os
from setuptools import find_packages, setup

CURDIR = os.path.abspath(os.path.dirname(__file__))

EXCLUDE_FROM_PACKAGES = []
REQUIRED = ["requests"]

with io.open(os.path.join(CURDIR, "README.md"), "r", encoding="utf-8") as f:
    README = f.read()

setup(
    name="pipx-app",
    version="0.9.2",
    author="Chad Smith",
    author_email="grassfedcode@gmail.com",
    description="execute binaries from Python packages in isolated environments",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/cs01/pipx",
    license="License :: OSI Approved :: MIT License",
    packages=find_packages(exclude=EXCLUDE_FROM_PACKAGES),
    include_package_data=True,
    keywords=["pip", "install", "cli", "virtualenv", "workflow"],
    scripts=[],
    entry_points={"console_scripts": ["pipx = pipx.main:cli"]},
    extras_require={},
    zip_safe=False,
    python_requires=">=3.6",
    install_requires=REQUIRED,
    classifiers=[
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3 :: Only",
    ],
)
